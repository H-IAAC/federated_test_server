import logging
from datetime import datetime
import requests
from pathlib import Path
from requests.packages.urllib3.filepost import encode_multipart_formdata

logging.getLogger('werkzeug').disabled = True

######
# Log message to default output.
#
#####
def log(msg):
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    print(f"{now} | {msg}")

    with open("./log.txt", "a") as file:
        file.write(f"{now} {msg}\n")

######
# 
#
#####
def check_log_size():
    with open("./log.txt", 'r+') as file:
        # read an store all lines into list
        lines = file.readlines()

        # Remove initial file lines, when it has more than 5000 log lines
        if len(lines) > 5000:
            print(f"-> removing log lines")
            # move file pointer to the beginning of a file
            file.seek(0)
            # truncate the file
            file.truncate()
            # start writing lines except the first line
            # lines[2500:] from line 2501 to last line
            file.writelines(lines[2500:])

######
# Read log content
#
#####
def read_log():
        with open("./log.txt", 'r+') as file:
            # loop to read iterate
            # last 1000 lines and print it
            file.seek(0)
            content = '<head><style>'
            content += 'body { font-family: "Courier New", monospace; }'
            content += '</style></head>'
            content += '<script> function scrollToBottom() { window.scrollTo(0, document.body.scrollHeight); } '
            content += 'history.scrollRestoration = "manual"; '
            content += 'window.onload = scrollToBottom; </script>'

            for line in (file.readlines()[-1000:]):
                content += line + "</br>"

            return content

######
#  Post request message
#
#####
def post_request(url, directory, file_path):
    log(f"Post file {file_path} to {url}")

    if Path(file_path).is_file():
        log(f"{file_path} exists, uploading...")
    else:
        log(f"{file_path} do not exists! Ignoring upload")
        return

    fields = {
            'directory': directory,
            "file": ("file", open(file_path).read()),
    }

    # Post request as multipart form data
    (content, header) = encode_multipart_formdata(fields)
    r = requests.post(url, data=content, headers={'Content-Type': header})

    log(f'Post response {r.status_code}')
