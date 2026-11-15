#document_reader.py

def read_document(attachment_path):
    pass

    #what type of attachment?
    #what type of pdf, be ready to convert false typings .pdf vs .ppdf 
    # what libraries can convert tables to md for the ai
    # how to parse the pdf for the AI? Pypdf? what if it's an image? -> OCR?


    #elif statements

    '''
    the problem here is that we have to be able to pull from the type of attachments (important context)
    What is important context here...? Basically 
    Convert all text/context -> MD for the AI layer to easily read! then put in pydantic

    How do we make sure we're not missing anything hmmmmm....Best method to splice from a pdf?
    pypdf, python also has ocr ...I guess this becomes a question of trusting an LLM with context eng to 
    view context in a file verus trusting in house python pacakges...

    what can I trust with python packages...pdf -> all pdfs? some pdfs can be images though...

    THE KEY:
    Don't make the LLM responsible for reading every file format. Use Python to extract the contents, normalize them into a consistent format,
    and then let the LLM interpret that content.

    Let's see how the program can perform with python packages verus handing over whole document to AI when needed...
    I feel like a combination of the two is the best case.
    Checking the pages ... hmmm! Maybe have a confidence score for each page! How good is the OCR score...Accuracy / precision 

    FIRST steps:
        grab the attachments via file extensions, in an elif statements handdle 

    

    '''