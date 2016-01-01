# blog2pdf

A python 2.7 script to extract the contents of a blog and create a PDF version for backup or offline viewing.

### Tools used:
* requests
* [beautiful soup 4](http://www.crummy.com/software/BeautifulSoup/bs4)
* [pylatex](https://github.com/JelteF/PyLaTeX)
* [dicttoxml] (https://github.com/quandyfactory/dicttoxml)
* pickle
* python's cmd

### Usage:
```
python blog2pdf.py

(cmd) set <username>   # configures to use username
(cmd) autoget          # pulls user data from the web, dumping any images encoutered
(cmd) save             # saves the data pulled
(cmd) json             # exports data to JSON file
(cmd) tex              # outputs a .tex for compiling and creating a PDF
```

#### Other commands:
```
(cmd) load             # loads a previously saved user data file
(cmd) getday YYYY DDD  # prints a summary of the given day's data
(cmd) xml              # exports data to XML file
(cmd) select           # (unimplemented) being interactive selection of posts for exporting to PDF
(cmd) analyse          # (unimplemented) examines the loaded current users data
```

### TODO list:
* Support for CJK characters in latex (perhaps 
* General unicode support (Segoe UI Symbol does a good job..)
* [Emoji support in latex](https://github.com/alecjacobson/coloremoji.sty)
* Correcting images without extensions on server
* Include more day and post information. Eg. day headers and comments
* More professional default layout (not starting new column inappropriately, [titles centered](http://tex.stackexchange.com/a/8547) etc )
* Other layout options
* script for json import into adobe InDesign
