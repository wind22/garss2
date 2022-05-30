import feedparser
import time
import os
import re
import pytz
import datetime
import yagmail
import requests
import markdown
import json
import shutil
from urllib.parse import urlparse
from multiprocessing import Pool,  Manager
import xml.etree.ElementTree as ET


def get_rss_info(feed_url, index, rss_info_list):
    result = {"result": []}
    request_success = False
    # 如果请求出错,则重新请求,最多五次
    for i in range(3):
        if(request_success == False):
            try:
                headers = {
                    # 设置用户代理头(为狼披上羊皮)
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36",
                    "Content-Encoding": "gzip"
                }
                # 三次分别设置8, 16, 24秒钟超时
                feed_url_content = requests.get(feed_url,  timeout= (i+1)*8 ,headers = headers).content
                feed = feedparser.parse(feed_url_content)
                feed_entries = feed["entries"]
                feed_entries_length = len(feed_entries)
                print("==feed_url=>>", feed_url, "==len=>>", feed_entries_length)
                for entrie in feed_entries[0: feed_entries_length-1]:
                    title = entrie["title"]
                    link = entrie["link"]
                    if entrie.has_key('author'):
                        author = entrie['author']
                    else:
                        author = '未知'
                    date = time.strftime("%Y-%m-%d", entrie["published_parsed"])
                    
                    title = title.replace("\n", "")
                    title = title.replace("\r", "")
                    author = author.replace('\n\r','')
                    result["result"].append({
                        "title": title,
                        "link": link,
                        "date": date,
                        'author':author
                    })
                request_success = True
            except Exception as e:
                print(feed_url+"第+"+str(i)+"+次请求出错==>>",e)
                pass
        else:
            pass

    rss_info_list[index] = result["result"]
    print("本次爬取==》》", feed_url, "<<<===", index, result["result"])
    # 剩余数量
    remaining_amount = 0

    for tmp_rss_info_atom in rss_info_list:
        if(isinstance(tmp_rss_info_atom, int)):
            remaining_amount = remaining_amount + 1
            
    print("当前进度 | 剩余数量", remaining_amount, "已完成==>>", len(rss_info_list)-remaining_amount)
    return result["result"]
    


def send_mail(email, title, contents):
    # 判断secret.json是否存在
    user = ""
    password = ""
    host = ""
    try:
        if(os.environ["USER"]):
            user = os.environ["USER"]
        if(os.environ["PASSWORD"]):
            password = os.environ["PASSWORD"]
        if(os.environ["HOST"]):
            host = os.environ["HOST"]
    except:
        print("无法获取github的secrets配置信息,开始使用本地变量")
        if(os.path.exists(os.path.join(os.getcwd(),"secret.json"))):
            with open(os.path.join(os.getcwd(),"secret.json"),'r') as load_f:
                load_dict = json.load(load_f)
                user = load_dict["user"]
                password = load_dict["password"]
                host = load_dict["host"]
                # print(load_dict)
        else:
            print("无法获取发件人信息")
    
    # 连接邮箱服务器
    # yag = yagmail.SMTP(user=user, password=password, host=host)
    yag = yagmail.SMTP(user = user, password = password, host=host)
    # 发送邮件
    yag.send(email, title, contents)


def get_mail_content(file_path):
    section_format_text = '| <h3 id="{cate}">{cate}</h3> |  |  |  |'
    rss_format_text = '|{rss_name} | {rss_description} | {latest_content} |  [订阅地址]({link}) |'
    section_format_html = '<h1 id="{cate}">{cate}</h1>'
    rss_format_html = '''<h3 id="{rss_name}"><a href="{link}">{rss_name}</a></h3>'''
    section_sep = '<HR style="border:1 dashed #35cb1e" width="100%" color=#987cb9 SIZE=10>'
    rss_seq = '<HR style="FILTER: progid:DXImageTransform.Microsoft.Shadow(color:#987cb9,direction:145,strength:15)" width="100%" color=#0d78cf SIZE=5>'
    new_edit_readme_md = ["", "", ""]
    current_date_news_index = [""]
    rss_list_format = []
    rss_link = []
    section_format_list = []
    rss_format_list = []
    rss_cate_list = []
    new_num = 0
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    today = today.strftime("%Y-%m-%d")
    yesterday = yesterday.strftime("%Y-%m-%d")
  
    with open(file_path,'r') as load_f:
        load_dic = json.load(load_f)
        cur_cate = ''
        for index, rss in enumerate(load_dic["rss_list"]):
            rss_link.append(rss['link'])
            section_format_list.append(section_format_html.format(cate=rss['cate']))
            rss_format_list.append(rss_format_html.format(link=rss['link'],rss_name=rss['rss_name']))
            rss_cate_list.append(rss['cate'])
            if rss['cate'] != cur_cate:
                rss_list_format.append(section_format_text.format(cate=rss['cate']))
                rss_list_format.append(rss_format_text.format(
                    cate=rss['cate']
                    ,rss_name=rss['rss_name']
                    ,rss_description = rss['rss_description']
                    ,link = rss['link']
                    ,latest_content = str(index) + 'latest_content'))
                cur_cate = rss['cate']
            else:
                rss_list_format.append(rss_format_text.format(
                    cate=rss['cate']
                    ,rss_name=rss['rss_name']
                    ,rss_description = rss['rss_description']
                    ,link = rss['link']
                    ,latest_content = str(index) + 'latest_content'))
                
                
    with open(os.path.join(os.getcwd(),"EditREADME2.md"),'r') as load_f:
        edit_readme_md = load_f.read()
        new_edit_readme_md[0] = edit_readme_md + '\n'.join(rss_list_format) + '\n' + '<邮件格式2结束'
        # 填充统计RSS数量
        new_edit_readme_md[0] = new_edit_readme_md[0].replace("{{rss_num}}", str(len(rss_link)))
        # 填充统计时间
        ga_rss_datetime = datetime.datetime.fromtimestamp(int(time.time()),pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        new_edit_readme_md[0] = new_edit_readme_md[0].replace("{{ga_rss_datetime}}", str(ga_rss_datetime))

    # 使用进程池进行数据获取，获得rss_info_list
    before_info_list_len = len(rss_link)
    rss_info_list = Manager().list(range(before_info_list_len))
    print('初始化完毕==》', rss_info_list)
    
    # 创建一个最多开启8进程的进程池
    po = Pool(8)

    for index, link in enumerate(rss_link):
        # 获取link
        po.apply_async(get_rss_info,(link, index, rss_info_list))


    # 关闭进程池,不再接收新的任务,开始执行任务
    po.close()

    # 主进程等待所有子进程结束
    po.join()
    print("----结束----", rss_info_list)
    
    
    cur_cate = ''
    for index, link in enumerate(rss_link):
        # 生成超链接
        rss_info = rss_info_list[index]
        latest_content = ""
        parse_result = urlparse(link)
        scheme_netloc_url = str(parse_result.scheme)+"://"+str(parse_result.netloc)
        latest_content = "[暂无法通过爬虫获取信息, 点击进入源网站主页]("+ scheme_netloc_url +")"

        # 加入到索引
        try:
            # if len(rss_info) > 0 and cur_cate != rss_cate_list[index]:
            #     current_date_news_index[0] = current_date_news_index[0] + section_format_list[index] + rss_format_list[index]
            #     cur_cate = rss_cate_list[index]
            # elif len(rss_info) > 0:
            #     current_date_news_index[0] = current_date_news_index[0] + rss_format_list[index]
            flag = 1
            for rss_info_atom in rss_info:
                if (rss_info_atom["date"] in [today,yesterday]):
                    new_num = new_num + 1
                    if cur_cate != rss_cate_list[index] and flag == 1:
                        current_date_news_index[0] += section_sep
                        current_date_news_index[0] = current_date_news_index[0] + section_format_list[index] + rss_format_list[index]
                        cur_cate = rss_cate_list[index]
                        flag = 0
                    elif flag == 1:
                        current_date_news_index[0] = current_date_news_index[0] + rss_format_list[index]
                        flag = 0
                    if (new_num % 2) == 0:
                        current_date_news_index[0] = current_date_news_index[0] + "<div style='line-height:3;' ><a href='" + rss_info_atom["link"] + "' " + 'style="line-height:2;text-decoration:none;display:block;color:#584D49;">' + "🌈 ‣ " + rss_info_atom["title"] + "</a></div>"
                    else:
                        current_date_news_index[0] = current_date_news_index[0] + "<div style='line-height:3;background-color:#FAF6EA;' ><a href='" + rss_info_atom["link"] + "' " + 'style="line-height:2;text-decoration:none;display:block;color:#584D49;">' + "🌈 ‣ " + rss_info_atom["title"] + "</a></div>"
                    print(current_date_news_index[0])
            if flag == 0:
                current_date_news_index[0] += rss_seq

        except:
            print("An exception occurred")
        

            
        for i, rss in enumerate(rss_info):
            if (rss["date"] == datetime.datetime.today().strftime("%Y-%m-%d")):
                rss["title"] = rss["title"].replace("|", "\|")
                rss["title"] = rss["title"].replace("[", "\[")
                rss["title"] = rss["title"].replace("]", "\]")
                if i == 0:
                    latest_content = "[" + "‣ " + rss["title"] + ( " 🌈 " + rss["date"] if (rss["date"] == datetime.datetime.today().strftime("%Y-%m-%d")) else " \| " + rss["date"] ) +"](" + rss["link"] +")"
                else:
                    latest_content = latest_content + "<br/>[" + "‣ " +  rss["title"] + ( " 🌈 " + rss["date"] if (rss["date"] == datetime.datetime.today().strftime("%Y-%m-%d")) else " \| " + rss["date"] ) +"](" + rss["link"] +")"
                

        # 生成after_info
        print(new_edit_readme_md[0])
        new_edit_readme_md[0] = new_edit_readme_md[0].replace(str(index) + "latest_content", latest_content)
        print("====latest_content==>", latest_content)
        
        
     # 替换EditREADME中的索引
    new_edit_readme_md[0] = new_edit_readme_md[0].replace("{{news}}", current_date_news_index[0])
    # 替换EditREADME中的新文章数量索引
    new_edit_readme_md[0] = new_edit_readme_md[0].replace("{{new_num}}", str(new_num))
        
    mail_re1 = r'邮件格式1开始>([.\S\s]*)<邮件格式1结束'
    mail_re2 = r'邮件格式2开始>([.\S\s]*)<邮件格式2结束'
    new_edit_readme_md[1] = re.findall(mail_re1, new_edit_readme_md[0])
    new_edit_readme_md[2] = re.findall(mail_re2, new_edit_readme_md[0])
        
    return new_edit_readme_md
# 将README.md复制到docs中

def cp_readme_md_to_docs():
    shutil.copyfile(os.path.join(os.getcwd(),"README.md"), os.path.join(os.getcwd(), "docs","README.md"))
    
def cp_media_to_docs():
    if os.path.exists(os.path.join(os.getcwd(), "docs","_media")):
        shutil.rmtree(os.path.join(os.getcwd(), "docs","_media"))	
    shutil.copytree(os.path.join(os.getcwd(),"_media"), os.path.join(os.getcwd(), "docs","_media"))

def get_email_list():
    email_list = []
    with open(os.path.join(os.getcwd(),"tasks.json"),'r') as load_f:
        load_dic = json.load(load_f)
        for task in load_dic["tasks"]:
            email_list.append(task["email"])
    return email_list

# 创建opml订阅文件

def create_opml():

    result = "";
    result_v1 = "";

    # <outline text="CNET News.com" description="Tech news and business reports by CNET News.com. Focused on information technology, core topics include computers, hardware, software, networking, and Internet media." htmlUrl="http://news.com.com/" language="unknown" title="CNET News.com" type="rss" version="RSS2" xmlUrl="http://news.com.com/2547-1_3-0-5.xml"/>

    with open(os.path.join(os.getcwd(),"EditREADME.md"),'r') as load_f:
        edit_readme_md = load_f.read();

        ## 将信息填充到opml_info_list
        opml_info_text_list =  re.findall(r'.*\{\{latest_content\}\}.*\[订阅地址\]\(.*\).*' ,edit_readme_md);

        for opml_info_text in opml_info_text_list:


            # print('==', opml_info_text)

            opml_info_text_format_data = re.match(r'\|(.*)\|(.*)\|(.*)\|(.*)\|.*\[订阅地址\]\((.*)\).*\|',opml_info_text)

            # print("data==>>", opml_info_text_format_data)

            # print("总信息", opml_info_text_format_data[0].strip())
            # print("编号==>>", opml_info_text_format_data[1].strip())
            # print("text==>>", opml_info_text_format_data[2].strip())
            # print("description==>>", opml_info_text_format_data[3].strip())
            # print("data004==>>", opml_info_text_format_data[4].strip())
            print('##',opml_info_text_format_data[2].strip())
            print(opml_info_text_format_data[3].strip())
            print(opml_info_text_format_data[5].strip())
            

            opml_info = {}
            opml_info["text"] = opml_info_text_format_data[2].strip()
            opml_info["description"] = opml_info_text_format_data[3].strip()
            opml_info["htmlUrl"] = opml_info_text_format_data[5].strip()
            opml_info["title"] = opml_info_text_format_data[2].strip()
            opml_info["xmlUrl"] = opml_info_text_format_data[5].strip()

            # print('opml_info==>>', opml_info);
            


            opml_info_text = '<outline  text="{text}" description="{description}" htmlUrl="{htmlUrl}" language="unknown" title="{title}" type="rss" version="RSS2" xmlUrl="{xmlUrl}"/>'

            opml_info_text_v1 = '      <outline text="{title}" title="{title}" type="rss"  \n            xmlUrl="{xmlUrl}" htmlUrl="{htmlUrl}"/>'

            opml_info_text =  opml_info_text.format(
                text=opml_info["text"], 
                description=opml_info["description"], 
                htmlUrl = opml_info["htmlUrl"],
                title=opml_info["title"],
                xmlUrl=opml_info["xmlUrl"]
            )

            opml_info_text_v1 =  opml_info_text_v1.format(
                htmlUrl = opml_info["htmlUrl"],
                title=opml_info["title"],
                xmlUrl=opml_info["xmlUrl"]
            )

            result = result + opml_info_text + "\n"

            result_v1 = result_v1 + opml_info_text_v1 + "\n"
    
    zhaoolee_github_garss_subscription_list = "";
    with open(os.path.join(os.getcwd(),"rss-template-v2.txt"),'r') as load_f:
        zhaoolee_github_garss_subscription_list_template = load_f.read();
        GMT_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'
        date_created = datetime.datetime.utcnow().strftime(GMT_FORMAT);
        date_modified = datetime.datetime.utcnow().strftime(GMT_FORMAT);
        zhaoolee_github_garss_subscription_list = zhaoolee_github_garss_subscription_list_template.format(result=result, date_created=date_created, date_modified=date_modified);
        # print(zhaoolee_github_garss_subscription_list);

    # 将内容写入
    with open(os.path.join(os.getcwd(),"zhaoolee_github_garss_subscription_list_v2.opml"),'w') as load_f:
        load_f.write(zhaoolee_github_garss_subscription_list)

    zhaoolee_github_garss_subscription_list_v1 = ""
    with open(os.path.join(os.getcwd(),"rss-template-v1.txt"),'r') as load_f:
        zhaoolee_github_garss_subscription_list_template = load_f.read();
        zhaoolee_github_garss_subscription_list_v1 = zhaoolee_github_garss_subscription_list_template.format(result=result_v1);
        # print(zhaoolee_github_garss_subscription_list_v1);

    # 将内容写入
    with open(os.path.join(os.getcwd(),"zhaoolee_github_garss_subscription_list_v1.opml"),'w') as load_f:
        load_f.write(zhaoolee_github_garss_subscription_list_v1)




        
    # print(result)

def get_rss_from_xml(rss_xml_dir_path):
    rss_source = []
    email_title = []
    files = os.listdir(rss_xml_dir_path)
    for file in files:
        rss_list = []
        if os.path.isfile(rss_xml_dir_path + os.sep +file):
            tree = ET.parse(rss_xml_dir_path + os.sep +file)
            root = tree.getroot()
            email_title.append(root.find('head').find('title').text)
            for cate in root.find('body'):
                category = cate.attrib.get('title')
                for rss in cate:
                    rss.attrib['cate'] = category
                    rss_list.append(rss.attrib)
            rss_source.append(rss_list)
    return rss_source,email_title

def get_email_template(file_path,rss_num):
    with open(file_path,'r') as load_f:
        email_content = load_f.read()
        # 填充统计RSS数量
        email_content = email_content.replace("{{rss_num}}", str(rss_num))
        # 填充统计时间
        ga_rss_datetime = datetime.datetime.fromtimestamp(int(time.time()),pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        email_content = email_content.replace("{{ga_rss_datetime}}", str(ga_rss_datetime))
        return email_content
    
    
def get_rss_info_mul_thread(rss_list):
    # 使用进程池进行数据获取，获得rss_info_list
    rss_info_list = Manager().list(range(len(rss_list))) 
    # 创建一个最多开启8进程的进程池
    po = Pool(8)
    for index, rss in enumerate(rss_list):
        # 获取link
        po.apply_async(get_rss_info,(rss['xmlUrl'], index, rss_info_list))
    # 关闭进程池,不再接收新的任务,开始执行任务
    po.close()
    # 主进程等待所有子进程结束
    po.join()
    return rss_info_list


def get_email_content_from_xml(rss_source,email_title):
    
    section_format_html = '<h2 id="{cate}">{cate}</h2>'
    rss_format_html = '''<h3 id="{rss_name}"><a href="{link}">{rss_name}</a></h3>'''
    # section_sep = '<HR style="border:1 dashed #35cb1e" width="100%" color=#987cb9 SIZE=10>'
    # rss_seq = '<HR style="FILTER: progid:DXImageTransform.Microsoft.Shadow(color:#987cb9,direction:145,strength:15)" width="100%" color=#0d78cf SIZE=5>'
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    today = today.strftime("%Y-%m-%d")
    yesterday = yesterday.strftime("%Y-%m-%d")
    
    section_sep = ''
    rss_seq = ''
    email_content_list = []
    
    for num, rss_list in enumerate(rss_source):            
        file_path = os.path.join(os.getcwd(),"email_template.md")       
        email_template_content = get_email_template(file_path,len(rss_list))
        rss_info_list = get_rss_info_mul_thread(rss_list)
        email_content = ''
        cur_cate = ''
        new_num = 0
        for index, rss in enumerate(rss_list):
            # 生成超链接
            rss_info = rss_info_list[index]
            
            # 加入到索引
            try:
                # if len(rss_info) > 0 and cur_cate != rss_cate_list[index]:
                #     email_content = email_content + section_format_list[index] + rss_format_list[index]
                #     cur_cate = rss_cate_list[index]
                # elif len(rss_info) > 0:
                #     email_content = email_content + rss_format_list[index]
                flag = 1
                for rss_info_atom in rss_info:
                    if (rss_info_atom["date"] in [today, yesterday]):
                        new_num = new_num + 1
                        if cur_cate != rss['cate'] and flag == 1:
                            email_content += section_sep
                            email_content += section_format_html.format(cate = rss['cate']) + rss_format_html.format(rss_name=rss['title'],link=rss['htmlUrl'])
                            cur_cate = rss['cate']
                            flag = 0
                        elif flag == 1:
                            email_content += rss_format_html.format(rss_name=rss['title'],link=rss['htmlUrl'])
                            flag = 0
                        if (new_num % 2) == 0:
                            email_content = email_content + "<div style='line-height:3;' ><a href='" + rss_info_atom["link"] + "' " + 'style="line-height:2;text-decoration:none;display:block;color:#584D49;">' + "🌈 ‣ " + rss_info_atom["title"] + "</a></div>"
                        else:
                            email_content = email_content + "<div style='line-height:3;background-color:#FAF6EA;' ><a href='" + rss_info_atom["link"] + "' " + 'style="line-height:2;text-decoration:none;display:block;color:#584D49;">' + "🌈 ‣ " + rss_info_atom["title"] + "</a></div>"
                        print(email_content)
                if flag == 0:
                    email_content += rss_seq

            except:
                print("An exception occurred")
        
        
        email_content = email_template_content.replace("{{news}}", email_content)
        email_content = email_content.replace("{{new_num}}", str(new_num))
        email_content = email_content.replace("{{email_title}}",email_title[num])
            
        mail_re = r'邮件格式开始>([.\S\s]*)<邮件格式结束'
        email_content = re.findall(mail_re, email_content)[0]
        email_content_list.append(email_content)
        
    return email_content_list    


def main():
    rss_source_path = os.path.join(os.getcwd(),"rss_source.json")
    create_opml()
    readme_md = get_mail_content(rss_source_path)
    
    with open(os.path.join(os.getcwd(),"README.md"),'w') as load_f:
        load_f.write(readme_md[0])
        
    content1 = readme_md[1][0]
    content2 = markdown.markdown(readme_md[2][0], extensions=['tables', 'fenced_code'])
    cp_readme_md_to_docs()
    cp_media_to_docs()
    email_list = get_email_list()
    
    try:
        send_mail(email_list, "嘎!RSS订阅", content1)
        # send_mail(email_list,"嘎!RSS订阅",content2)
    except Exception as e:
        print("==邮件设信息置错误===》》", e)


    rss_xml_dir_path = os.path.join(os.getcwd(),"rss_xml")
    rss_source,email_title = get_rss_from_xml(rss_xml_dir_path)
    email_content_list = get_email_content_from_xml(rss_source,email_title)

    for email_content in email_content_list:
        try:
            send_mail(email_list, "嘎!RSS订阅", email_content)
            # send_mail(email_list,"嘎!RSS订阅",content2)
        except Exception as e:
            print("==邮件设信息置错误===》》", e)
if __name__ == "__main__":
    main()
