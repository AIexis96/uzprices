from io import BytesIO
import boto3
import time
import requests
from bs4 import BeautifulSoup
from secrets import access_key, secret_access_key

timestr = time.strftime ("%Y%m%d")
fname = 'prices_' + timestr + '.xlsx'
s3 = boto3.client('s3', aws_access_key_id = access_key, aws_secret_access_key = secret_access_key)

def load_new_file():      
    # Upload a new file to AWS S3
    
    r=requests.get("https://uz.gov.ua/passengers/suburban_train_schedule/", headers={'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0'})
    c=r.content
    soup=BeautifulSoup(c, "html.parser")
    all=soup.find_all("div", {"class":"content"})
    a=all[0].find_all("a")[2]
    h=a.get("href")
    link = "https://uz.gov.ua/" + h
    resp = requests.get(link)
    f = BytesIO (resp.content)
    
    s3.upload_fileobj(f, "uzprices", fname)
    return "Loaded succesfuly"

def compare_files():
    #Compare old and new files in AWS S3 bucket, remove duplicates

    bucketName = 'uzprices'
    response = s3.list_objects_v2(Bucket=bucketName)
    c = response['Contents']
    etag_old = c[-2]['ETag']
    etag_new = c[-1]['ETag']
    is_duplicate = (etag_new == etag_old)
    if is_duplicate:
        response = s3.delete_object(Bucket=bucketName, Key=c[-2]['Key'])
        return response
    else:
        return "New file was added"

def main():
    load_new_file()
    compare_files()

if __name__ == "__main__":
    main()