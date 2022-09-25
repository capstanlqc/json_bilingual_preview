#!/usr/bin/env python3

import argparse
import sys, re, os, glob, pprint, time
from yawrap import Yawrap, EmbedCss, EmbedJs, BODY_END
import json

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup

# ############# PROGRAM DESCRIPTION ###########################################

text = "This program converts a bilingual JSON file (from TALIS) to an \
  HTML table, showing the formatting of both source and target text, as well \
  as metadata. The HTML file is written in PROJ/preview/original.html"

# intialize arg parser with a description
parser = argparse.ArgumentParser(description=text)
parser.add_argument("-V", "--version", help="show program version",
                    action="store_true")
parser.add_argument("-p", "--project", help="specify path to OmegaT project folder")
parser.add_argument("-f", "--file", help="specify path to JSON file")

# example:
# config="/media/data/data/company/IPSOS/EUROBAROMETER_FLASH_2.0/_tech/Config/config.ods"
# json_fpath="/media/data/data/company/IPSOS/EUROBAROMETER_FLASH_2.0/08_FLASH_PROJECTS/FLASH-001-TEST/00_source/S21007984_x0_multi__internal use_20210312_153243.xlsm"
# python3 flash_prepp_extract.py -p "$json_fpath"
# this is called by the flash_init.sh script

# read arguments from the command line
args = parser.parse_args()

# check for -V or --version
if args.version:
    print("This is bilingual preview generator 0.1")
    sys.exit()

if args.project and args.file:
    json_fpath = args.file.rstrip('/')
    proj_dpath = args.project.rstrip('/')
else:
    print("Arguments -p or -f not found.")
    sys.exit()


# ############# FUNCTIONS ###########################################

def remove_enclosing_paired_tag(node):
    results = re.findall(r"^<(p|ul|li|ol)[^>]*>[\r\n]*([\s\S]+?)[\r\n]*</\1>$", node.strip())
    if not results:
        return node
    elif len(results[0]) == 2:
        node = remove_enclosing_paired_tag(results[0][1])
        return node
    else:
        pass


def make_bilingual_preview(json_fpath, proj_dpath):

    if not os.path.isfile(json_fpath):
        python(f"File {json_fpath} not found, unable to proceed.") # logging.error
        return False

    script = '''\
            /* change directionality if the target language is Arabic (and derivates) or Hebrew */
            const bodyText = document.body.innerText
            const regex = /\p{Script=Arabic}|\p{Script=Hebrew}/u
            const bidiFound = bodyText.match(regex)
            if (bidiFound) {  document["dir"] = "rtl" }

            // put a handler on the search box
            idSearch = document.querySelector('#idSearch')

            // focus search box when user presses Ctrl+F or F3
            document.addEventListener("keydown",function (e) {
              if (e.keyCode === 114 || (e.ctrlKey && e.keyCode === 70)){
                e.preventDefault()
                idSearch.focus()
              }
            })

            // go to row when user presses enter
            idSearch.addEventListener('keypress', function(e){
              if (e.key == 'Enter') {
                segmentId = idSearch.value.trim()
                segment = document.getElementById(segmentId)
                segment.scrollIntoView({behavior: "smooth", block: "center", inline: "center"})
                // highlight location
                const url = location.href
                location.href = '#id'+segmentId
                history.replaceState(null,null,url);   //Don't like hashes. Changing it back.
              }
            })'''

    style = '''\
            body {
                max-width: 85%;
                min-width: 700px;
                margin: auto;
                padding: 40px;
            }
            div.search {
                display: inline-block;
            }
            input, label, div.item_label, div.textblock_id {
                display: block;
            }
            .id {
                font-size: x-small;
            }
            .table {
                display: grid;
                grid-template-columns: auto 40% 40%;
            }
            .table > div {
                margin: 2px;
                background: #CDCDCD;
                padding: 5px;
            }
            .table > div:nth-child(3n+2) {
                background: #eee;
            }
            .table > div:nth-child(3n+3) {
                background: #eee;
            }
            :target {
                background: yellow !important;
            }
            .sticky {
                z-index: 1;
                position: fixed;
                top: 125px;
                left:20px;
                margin: 30;
                border: 0px gray solid;
                /* not sticky properties, but I add them here */
                float: right;
                margin-right: 10;
            }'''


    path_to_html_file = os.path.join(proj_dpath, 'preview', "original.html")

    jawrap = Yawrap(path_to_html_file)
    jawrap.add(EmbedCss(style))
    jawrap.add(EmbedJs(script, placement=BODY_END))


    with open(json_fpath, encoding="utf-8-sig") as json_file:
        data = json.load(json_file)

    h1 = f"{data['study']} - {data['instrument']} [{data['culture']}]"
    textblocks = data['Textblocks']

    with jawrap.tag("h1"):
        jawrap.text(h1)
    with jawrap.tag("div", klass="search sticky"):
        with jawrap.tag("label"):
            jawrap.text("ID search")
        with jawrap.tag("input", type="text", id="idSearch", size="6", maxlength="5"):
            jawrap.text()

    with jawrap.tag("div", klass="table"):
        for entry in textblocks:
            i = textblocks.index(entry)
            textblock_id = entry["textblock_id"]
            item_label = entry["item_label"]


            source_text = remove_enclosing_paired_tag(entry["source_text"])
            target_text = remove_enclosing_paired_tag(entry["target_text"])
            comments = entry["comments"]

            #jawrap.text(html.escape(row.value))
            # escape < and > without altering html tags
            with jawrap.tag("div", id=textblock_id, klass="id"):
                with jawrap.tag("div", id="id"+str(textblock_id), klass=textblock_id):
                    jawrap.text(textblock_id)
                with jawrap.tag("div", klass=item_label):
                    jawrap.text(item_label)
            with jawrap.tag("div", id="src"+str(textblock_id)):
                escaped_source_text = BeautifulSoup(source_text, "html.parser")
                jawrap.text(escaped_source_text)
            with jawrap.tag("div", id="tgt"+str(textblock_id)):
                escaped_target_text = BeautifulSoup(target_text, "html.parser")
                jawrap.text(escaped_target_text)

    jawrap.render()

    return path_to_html_file



if __name__ == "__main__":
    # file = "/home/souto/Sync/TALIS24/02_Work/TALIS24_test4_20220925_OMT/orig/SE_TALIS_FT_HUN_hu-HU_20220921124639862.json" # get it with arg parse
    make_bilingual_preview(json_fpath, proj_dpath)
