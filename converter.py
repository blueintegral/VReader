
import shutil
import sys
import subprocess
import os
import os.path
import textwrap
import unicodedata
from pyPdf import PdfFileWriter, PdfFileReader
from ebooklib import epub
from bs4 import BeautifulSoup
from unidecode import unidecode
from time import sleep

def append_pdf(input,output):
    [output.addPage(input.getPage(page_num)) for page_num in range(input.numPages)]

# Print iterations progress
def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, bar_length=100):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        bar_length  - Optional  : character length of bar (Int)
    """
    str_format = "{0:." + str(decimals) + "f}"
    percents = str_format.format(100 * (iteration / float(total)))
    filled_length = int(round(bar_length * iteration / float(total)))
    bar = '*' * filled_length + '-' * (bar_length - filled_length)

    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percents, '%', suffix)),

    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()

if __name__ == "__main__":
    book_path = raw_input("What's the absolute path to the epub you want to convert? ")
    assert os.path.exists(book_path), "File not found at, "+str(book_path)
    assert book_path.endswith(".epub"), "File must be .epub. Cannot convert "+str(book_path)
    lines_per_page = 16
    characters_per_line = 30

    book = epub.read_epub(book_path)
    #book = epub.read_epub("C:\pg74.epub") #Read in the ebook
    raw_text = ""
    pdf_number = 0
    #make a temporary directory to store image files we create
    if not os.path.isdir("vreadconvert_tmp"):
        os.mkdir("vreadconvert_tmp")

    #First extract all the text using BeautifulSoup, since an epub is just html
    for item in book.items:
    	if isinstance(item, epub.EpubHtml):
    		soup = BeautifulSoup(item.content, 'lxml')
    		raw_text = raw_text + " " + soup.text

    raw_text = unidecode(raw_text).replace('"','\\"')
    raw_text = raw_text.replace('&','and')
    #We have to use unidecode because the epub input is unicode and uses stupid things like fancy quotes, 
    #so using unicodedata.normalize doesn't work. unidecode I think is basically a lookup table that
    #replaces unicode characters with ones that seem close in ascii.

    #Now chunk the text into page sized pieces
    chunks = textwrap.wrap(raw_text, characters_per_line)
    outputname = 0
    total_length = len(chunks)
    printProgressBar(0, total_length, prefix = 'Progress:', suffix = 'Complete', bar_length = 50)
    while(chunks): #change this to while(chunks) for non-test mode, len(chunks) > 14000) for test mode
        #print "Chunks left: "+str(len(chunks))
        printProgressBar(total_length - len(chunks), total_length, prefix = 'Progress:', suffix = 'Complete', bar_length = 50)
        lines = ""
        if len(chunks) > lines_per_page:
            for i in range(0,lines_per_page):
        		lines = lines + chunks[i]+ "\\n" #Break the text up into single pages for the ereader screen
        elif len(chunks) <= lines_per_page: #The very last page might not have enough lines for an entire page, so handle that here
            for i in range(0, len(chunks)):
                lines = lines + chunks[i]+ "\\n"
        #First step is to convert those lines to an image
        convert_args = ['convert', '-strip', '-interlace', 'plane', '-quality', '85%', '-size', '1200x1100', 'xc:white', '-fill', 'black', '-pointsize', '56', '-gravity', 'center', '-annotate', '+0+0', lines, 'vreadconvert_tmp/'+str(outputname)+".jpg"]
        subprocess.call(convert_args, shell=True)
        #print convert_args
        #Next we create the stereo version of that image for the goggles
        subprocess.call( ['montage', 'vreadconvert_tmp/'+str(outputname)+".jpg", 'vreadconvert_tmp/'+str(outputname)+".jpg", "-tile", "2x1", "-geometry", "+0+0", 'vreadconvert_tmp/'+str(outputname)+".jpg"])
        #Finally we attempt to compress the resulting image a little
        subprocess.call( ['convert', '-strip', '-interlace', 'plane', '-rotate', '90', '-quality', '85%', 'vreadconvert_tmp/'+str(outputname)+".jpg", 'vreadconvert_tmp/'+str(outputname)+".jpg"], shell=True)
        chunks = chunks[lines_per_page:] #Remove chunks we already converter
        outputname = outputname + 1
       
    #Now build up the command to run to combine all images in order to make the final PDF
    image_list = []
    #make a list of every image
    outputnames = []
    for i in range(0, outputname-1):
        outputnames.append(i)

    while(len(outputnames) > 300):
        image_list = []
        for i in range(outputnames[0], outputnames[0]+300):
            image_list.append("vreadconvert_tmp/"+str(i)+".jpg")
        image_list = ["convert"] + image_list
        image_list.append("-quality")
        image_list.append("85%")
        pdf_name = os.path.basename(book_path)
        pdf_name = os.path.splitext(pdf_name)[0]
        image_list.append(pdf_name+str(pdf_number)+".pdf")
        pdf_number = pdf_number + 1
        print image_list
        subprocess.call( image_list, shell=True)
        outputnames = outputnames[outputnames[0]+300:]
    print "outputnames is now "+str(outputnames)
    image_list = []    
    for i in range(outputnames[0], outputnames[0]+len(outputnames)):
        image_list.append("vreadconvert_tmp/"+str(i)+".jpg")
    image_list = ["convert"] + image_list
    image_list.append("-quality")
    image_list.append("85%")
    pdf_name = os.path.basename(book_path)
    pdf_name = os.path.splitext(pdf_name)[0]
    image_list.append(pdf_name+str(pdf_number)+".pdf")
    print image_list
    subprocess.call( image_list, shell=True)

    #now combine PDFs
    output = PdfFileWriter()
    for i in range(0, pdf_number):
        append_pdf(PdfFileReader(file(pdf_name+str(i)+".pdf","rb")),output)
    print "Combining PDFs"
    output.write(file(book_path[:-4]+"pdf","wb")) #put it back in the original epub directory
    
    #Now delete temporary directory
    shutil.rmtree("vreadconvert_tmp")
