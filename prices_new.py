from flask import Flask, render_template
import pandas
import boto3
import io
from bokeh.plotting import figure
from bokeh.models import Range1d
from bokeh.embed import components
from bokeh.resources import CDN
from secrets import access_key, secret_access_key

app=Flask(__name__)

@app.route("/plot/")
def plot():
    s3 = boto3.client('s3', aws_access_key_id = access_key, aws_secret_access_key = secret_access_key)
    bucketName = 'uzprices'
    response = s3.list_objects_v2(Bucket=bucketName)
    key = response['Contents'][-1]['Key']
    bytes_buffer = io.BytesIO()
    s3.download_fileobj(Bucket=bucketName, Key=key, Fileobj=bytes_buffer)
    file = bytes_buffer.getvalue()
    df=pandas.read_excel(file)

    row = df.iloc[2,:][df.iloc[2,:].notna()]
    regions = row[row.notna()]

    j = regions.count() 
    rr = [[] for j in range(j+1)]
    for i in range(regions.count()):
        if regions[i] == "Відстань":
            i = i + 1
        elif regions[i].startswith("Єдина в межах філії"):
            rr[i] = regions [i]
            i = i + 2
        else:
            rr[i] = regions [i]
    rr[:] = [x for x in rr if x]


    dl = {}
    j = 0
    k = 0
    for i in range(regions.count()):
        if df.iloc[2,i] == "Відстань" and str(df.iloc[1,i]) != "NaN":
            continue
        elif str(df.iloc[2,i]) == "nan":
            d = {str(df.iloc[2,i+1]):str(df.iloc[1,i-1])}
        elif str(df.iloc[2,i]).startswith("Єдина в межах філії"):
            d = {str(df.iloc[2,i]):str(df.iloc[1,i-1])}
            i = i + 2
        else:
            for n in range (regions.count()):
                if str(df.iloc[2,i-n]) == "Відстань" and str(df.iloc[1,i-n]) != "nan":   
                    if j != 0:
                        k = i-j                    
                    j = i                 
                    d = {str(df.iloc[2,i]):str(df.iloc[1,i-n])}           
                    if k > 1:
                        d[str(df.iloc[2,i])] = str(df.iloc[1,i-n])+str(k-1)
                    break                
        dl.update(d)

    kms_all = []
    for i in range(df.shape[1]):
        if df.iloc[2,i] == "Відстань":
            j = 0
            kms_list = []
            if str(df.iloc[1,i]) != 'nan':
                kms_list.append(df.iloc[1,i])
            else:
                j = j + 1
                r = kms_all[-1][0] + str(j)
                kms_list.append(r)
            for j in range (3, df.shape[0]):
                if str(df.iloc[j,i]) != 'nan' :
                    kms = list(range(int(df.iloc[j,i].partition('-')[0]),int(df.iloc[j,i].partition('-')[2])+1))
                    kms_list.append(kms)
            kms_all.append(kms_list)
    prices_list = []
    for i in range(df.shape[1]):
        for reg in rr:
            if df.iloc[2,i] == reg:
                prices_reg = []
                for j in range (2, df.iloc[:,i].dropna().shape[0]+2):
                    if str(df.iloc[j,i]) != 'nan':
                        p = df.iloc[j,i]
                        if isinstance (p, str) and p[::-1].find(',', 1, 4) == 2:
                            p = float(p.replace(',','.'))
                    prices_reg.append(p)
                prices_list.append(prices_reg)

    k = len(rr)
    list_dict_kms = []
    for i in range(k):
        dict_kms = {}
        if prices_list[i][0].startswith("Єдина в межах філії") and not ([*prices_list[i-1]][0].startswith("Єдина в межах філії")):
            j = len(kms_all[i-1])
            for m in range (1,j):
                d = dict.fromkeys(kms_all[i-1][m],prices_list[i][m])
                dict_kms.update(d)
        else:     
            for n in range (len(kms_all)):
                j = len(kms_all[n])
                for m in range (1,j):
                    if dl.get(prices_list[i][0]) == kms_all[n][0]:                        
                        d = dict.fromkeys(kms_all[n][m],prices_list[i][m])
                        dict_kms.update(d)
        list_dict_kms.append(dict_kms)
        
    for i in range(len(rr)):
        if rr[i].startswith("Єдина в межах філії"):
            rr[i] = dl[rr[i]]
        elif rr[i] == "Одеська обл. (швидкісні прим.поїзди Одеса-Ізмаїл-Одеса)":
            rr[i] = "Одеса — Ізмаїл"
        
    list_of_keys = []
    list_of_values = []
    max_of_k = []
    max_of_v = []
    for d in list_dict_kms:
        list_of_keys.append(list(d.keys()))
        list_of_values.append(list(d.values()))
        max_of_k.append(max(list_of_keys[-1]))
        max_of_v.append(max(list_of_values[-1]))
    max_x = max(max_of_k)
    max_y = max(max_of_v)

    xr = Range1d(start=0, end=max_x + 10)
    yr = Range1d(start=0, end=max_y + 70)

    p = figure(x_range=xr, y_range=yr, plot_width=1200, plot_height=800, sizing_mode="scale_width")
    p.xaxis.axis_label = "км"
    p.yaxis.axis_label = "грн"
    colors = ["red", "green", "blue", "gray", "black", "orange", "lime", "purple", "yellow", "brown", "cyan", "olive"]

    for n in range(k):
        p.line (list_of_keys[n], list_of_values[n], color = colors[n], legend_label = rr[n], line_width = 4, alpha = 0.65)

    p.legend.location = "top_left"

    script1, div1 = components(p)
    cdn_js=CDN.js_files[0]
    return render_template("plot.html", script1=script1, div1=div1, cdn_js=cdn_js)

@app.route("/")
def home():
    s3 = boto3.client('s3', aws_access_key_id = access_key, aws_secret_access_key = secret_access_key)
    bucketName = 'uzprices'
    response = s3.list_objects_v2(Bucket=bucketName)
    key = response['Contents'][-1]['Key']
    bytes_buffer = io.BytesIO()
    s3.download_fileobj(Bucket=bucketName, Key=key, Fileobj=bytes_buffer)
    file = bytes_buffer.getvalue()
    df=pandas.read_excel(file)

    row = df.iloc[2,:][df.iloc[2,:].notna()]
    regions = row[row.notna()]
    j = regions.count() 
    rr = [[] for j in range(j+1)]
    for i in range(regions.count()):
        if regions[i] == "Відстань":
            i = i + 1
        elif regions[i].startswith("Єдина в межах філії"):
            rr[i] = regions [i]
            i = i + 2
        else:
            rr[i] = regions [i]
    rr[:] = [x for x in rr if x]
    
    dl = {}
    j = 0
    k = 0
    for i in range(regions.count()):
        if df.iloc[2,i] == "Відстань" and str(df.iloc[1,i]) != "NaN":
            continue
        elif str(df.iloc[2,i]) == "nan":
            d = {str(df.iloc[2,i+1]):str(df.iloc[1,i-1])}
        elif str(df.iloc[2,i]).startswith("Єдина в межах філії"):
            d = {str(df.iloc[2,i]):str(df.iloc[1,i-1])}
            i = i + 2
        else:
            for n in range (regions.count()):
                if str(df.iloc[2,i-n]) == "Відстань" and str(df.iloc[1,i-n]) != "nan":   
                    if j != 0:
                        k = i-j                    
                    j = i                 
                    d = {str(df.iloc[2,i]):str(df.iloc[1,i-n])}           
                    if k > 1:
                        d[str(df.iloc[2,i])] = str(df.iloc[1,i-n])+str(k-1)
                    break                
        dl.update(d)
    kms_all = []
    for i in range(df.shape[1]):
        if df.iloc[2,i] == "Відстань":
            j = 0
            kms_list = []
            if str(df.iloc[1,i]) != 'nan':
                kms_list.append(df.iloc[1,i])
            else:
                j = j + 1
                r = kms_all[-1][0] + str(j)
                kms_list.append(r)
            for j in range (3, df.shape[0]):
                if str(df.iloc[j,i]) != 'nan' :
                    kms = list(range(int(df.iloc[j,i].partition('-')[0]),int(df.iloc[j,i].partition('-')[2])+1))
                    kms_list.append(kms)
            kms_all.append(kms_list)
    prices_list = []
    for i in range(df.shape[1]):
        for reg in rr:
            if df.iloc[2,i] == reg:
                prices_reg = []
                for j in range (2, df.iloc[:,i].dropna().shape[0]+2):
                    if str(df.iloc[j,i]) != 'nan':
                        p = df.iloc[j,i]
                        if isinstance (p, str) and p[::-1].find(',', 1, 4) == 2:
                            p = float(p.replace(',','.'))
                    prices_reg.append(p)
                prices_list.append(prices_reg)

    k = len(rr)
    list_dict_kms = []
    for i in range(k):
        dict_kms = {}
        if prices_list[i][0].startswith("Єдина в межах філії") and not ([*prices_list[i-1]][0].startswith("Єдина в межах філії")):
            j = len(kms_all[i-1])
            for m in range (1,j):
                d = dict.fromkeys(kms_all[i-1][m],prices_list[i][m])
                dict_kms.update(d)
        else:     
            for n in range (len(kms_all)):
                j = len(kms_all[n])
                for m in range (1,j):
                    if dl.get(prices_list[i][0]) == kms_all[n][0]:                        
                        d = dict.fromkeys(kms_all[n][m],prices_list[i][m])
                        dict_kms.update(d)
        list_dict_kms.append(dict_kms)

    table = {'км':['1-5','6-10','11-20','21-30','31-40','41-50','51-60','61-70','71-80','81-90','91-100','101-110','111-120','121-130','131-140','141-150','151-160','161-170','171-180','181-190','191-200','201-210','211-220','221-230','231-250','251-260','261-290','291-300','301-320','321-350']}
    df_table = pandas.DataFrame(table)
    kms=list(df_table['км'])
    keys_kms = []
    for km in kms:
        key_km=int(km.partition('-')[0])
        keys_kms.append(key_km)
    
     
    columns = []
    for d in list_dict_kms: 
        col = []
        for key in keys_kms:
            if key in d.keys():
                col.append(d[key])
        columns.append(col)

    for i in range(k):
        if rr[i].startswith("Єдина в межах філії"):
            rr[i] = dl[rr[i]]
        elif rr[i] == "Одеська обл. (швидкісні прим.поїзди Одеса-Ізмаїл-Одеса)":
            rr[i] = "Одеса — Ізмаїл"               
        df_table[rr[i]] = pandas.Series(columns[i])
                
    table_html = df_table.to_html(na_rep=' ', col_space='70px', index=False, justify='left')

    return render_template("home.html", script=table_html)

if __name__=="__main__":
    app.run(debug=True)