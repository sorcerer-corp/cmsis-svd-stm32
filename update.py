import zipfile
import logging
import json
import os, re, sys
import tempfile
import shutil
import subprocess
from urllib.request import urlopen, Request
from pathlib import Path

_hdr = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'none',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive'
}

def download_svd_data():
    url  = "https://www.st.com/content/st_com/en/products/microcontrollers-microprocessors/"
    url += "stm32-32-bit-arm-cortex-mcus.cxst-rs-grid.html/CL1734.cad_models_and_symbols.svd.json"
    with urlopen(Request(url, headers=_hdr)) as data:
        json_data = data.read().decode(encoding="utf-8", errors="ignore")
    rows = json.loads(json_data)["rows"]
    return [(row["localizedDescriptions"]["en"].split(" ")[0], row["version"],
             "https://www.st.com" + row["localizedLinks"]["en"]) for row in rows]

def download_zip(url, path):
    if path.exists(): path.unlink()
    with tempfile.NamedTemporaryFile() as outfile:
        os.system(f'wget -q --user-agent="{_hdr["User-Agent"]}" "{url}" -O {outfile.name}')
        shutil.copy(outfile.name, str(path))


def download_families(download = True):
    families = []
    if download:
        shutil.rmtree("raw", ignore_errors=True)
        Path("raw").mkdir(exist_ok=True)
    for family, version, url in sorted(download_svd_data()):
        print(family, version, url)
        if download:
            download_zip(url, Path(f"raw/{family.lower()}.zip"))
        families.append((family, version))
    return families

def format_readme(families):
    readme = Path("README.md")
    readme_families = "\n".join(f"- {f}: v{v}" for f, v in families)
    readme_families = f"<!--families-->\n{readme_families}\n<!--/families-->"
    readme.write_text(re.sub("<!--families-->.*?<!--/families-->", readme_families,
                             readme.read_text(), flags=re.DOTALL | re.MULTILINE))

def unzip_families(families):
    for family, _ in families:
        family = family.lower()
        pfam = Path(family)
        shutil.rmtree(pfam, ignore_errors=True)
        pfam.mkdir()
        with zipfile.ZipFile(Path(f"raw/{family}.zip")) as fzip:
            print(f"Unzipping raw/{family}.zip ...")
            rawpath = Path(f"raw/{family}")
            fzip.extractall(rawpath)
            for filename in fzip.namelist():
                if filename.endswith(".svd"):
                    # Copy, normalize newline and remove trailing whitespace
                    with (rawpath / filename).open("r", newline=None, encoding="utf-8", errors="ignore") as rfile, \
                        (pfam / Path(filename).name).open("w", encoding="utf-8") as wfile:
                        wfile.writelines(l.rstrip()+"\n" for l in rfile.readlines())


def commit_changes():
    subprocess.run("git add README.md stm32*", shell=True)
    if subprocess.call("git diff-index --quiet HEAD --", shell=True):
        subprocess.run('git commit -m "Update STM32 SVD files"', shell=True)


families = download_families("-d" in sys.argv)
format_readme(families)
unzip_families(families)
if "-c" in sys.argv:
    commit_changes()
