# blog2pdf

A python 2.7 script to extract the contents of a blog and create a PDF version for backup or offline viewing.

Tools used:
* requests
* beautiful soup 4
* pylatex
* pickle
* python's cmd

Usage:
python blog2pdf.py

(cmd) set <username>   # configures to use username
(cmd) autoget          # pulls user data from the web, dumping any images encoutered
(cmd) save             # saves the data pulled
(cmd) tex              # outputs a .tex for compiling and creating a PDF

Other commands:
(cmd) load             # loads a previously saved user data file
(cmd) getday YYYY DDD  # prints a summary of the given day's data
(cmd) select           # (still to come) being interactive selection of posts for exporting to PDF
(cmd) analyse          # (still to come) examines the loaded current users data

