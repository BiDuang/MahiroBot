import time
import json
import requests
import base64
import random

#基本文件IO
logFileName = 'BotLog_'+str(int(time.time()))+'.log'
logLenth = 0

def logPrint(strInput):
    global logFileName
    global logLenth
    if(logLenth>=1000):
        logLenth = 0
        logFileName = 'BotLog_'+str(int(time.time()))+'.log'
    logFile = open(logFileName, 'a+',encoding='utf-8')
    logFile.write(strInput+"\n")
    logLenth+=1
    logFile.close()
    print(strInput)

def jsonRead(fileName):
    fileCache = open(fileName,"r",encoding="utf-8")
    jsonContent = json.loads(fileCache.read())
    fileCache.close()
    return jsonContent

def jsonWrite(fileName,jsonContent):
    fileCache = open(fileName,"w",encoding="utf-8")
    fileCache.write(json.dumps(jsonContent,ensure_ascii=False))
    fileCache.close()

def fileWrite(fileName,contentCache,isb64=False):
    fileCache = open(fileName,"w",encoding="utf-8")
    if(isb64 == False):
        b64Cache = base64.b64encode(contentCache).decode()
        fileCache.write(b64Cache)
    else:
        fileCache.write(contentCache)
    fileCache.close()

def fileRead(fileName):
    fileCache = open(fileName,"r",encoding="utf-8")
    returnCache = fileCache.read()
    fileCache.close()
    return returnCache

#基本HTTP IO
def netGet(getUrl,urlType,isJson = False,isError = False):
    contentGet = requests.get(getUrl)
    if(netError(contentGet.status_code,str(contentGet),urlType=urlType,isError=isError)==1):
        contentGet.close()
        return 1
    contentGet.close()
    if(isJson==True):
        return json.loads(contentGet.text)
    else:
        return contentGet.content

def netPost(postUrl,urlType,jsonContent,isError = True,returnType = "json"):
    contentPost = requests.post(postUrl,json.dumps(jsonContent))
    if(netError(contentPost.status_code,str(contentPost),urlType=urlType,isError=isError)==1):
        contentPost.close()
        return 1
    else:
        contentPost.close()
        if(returnType == "json"):
            return json.loads(contentPost.text)
        else:
            return contentPost.text

def netError(statusCode,statusText,urlType,isError):
    global errorCount
    if(statusCode!=200):
        logPrint("[ERROR] Network Error ("+urlType+"). Code: "+statusText)
        if(isError == True):
            errorCount+=1
        return 1
    return None

#基本HTTP API交互
targetGroup = 0
apiUrl = ""
errorCount = 0
sendMessageChain = []

def messageList_get():
    global apiUrl
    global errorCount
    tempUrl = apiUrl+"fetchMessage"
    messageTemp = netGet(tempUrl,"Mirai",isJson=True,isError=True)
    if(messageTemp == 1):
        return []
    if(messageTemp["code"]==0):
        return messageTemp["data"]
    else:
        logPrint("[ERROR] MiraiAPI Error. Code: "+str(messageTemp["code"])+" Message: "+messageTemp["msg"])
        errorCount+=1
        return []

def singleMessage_Get(messageID):
    global apiUrl
    global errorCount
    global targetGroup
    messageCache = netGet(apiUrl+"/messageFromId?messageId="+str(messageID)+"&target="+str(targetGroup),"Mirai",isJson=True,isError=True)
    if(messageCache == 1):
        return None
    if(messageCache["code"] == 5):
        logPrint("[ERROR] MiraiAPI Error. Code: "+str(messageCache["code"])+" Message: "+messageCache["msg"])
        return None
    elif(messageCache["code"] == 0):
        return messageCache["data"]
    else:
        logPrint("[ERROR] MiraiAPI Error. Code: "+str(messageCache["code"])+" Message: "+messageCache["msg"])
        errorCount+=1
        return None

def messageChain_send():
    global targetGroup
    global apiUrl
    global errorCount
    global sendMessageChain
    if(errorCount>=10):
        logPrint("[ERROR] Too much errors.")
        return None
    if(len(sendMessageChain)==0):
        return None
    postMessage = {"target":targetGroup,"messageChain":sendMessageChain}
    postEvent = netPost(apiUrl+"sendGroupMessage","Mirai",postMessage)
    if(postEvent==1):
        messageChain_send()
    elif(postEvent["code"]!=0):
        logPrint("[ERROR] MiraiAPI Error. Code: "+str(postEvent["code"])+" Message: "+postEvent["msg"])
        errorCount+=1
        messageChain_send()
    else:
        logPrint("[INFO] BotSendMessageChain: Post success. "+str(len(sendMessageChain))+" message(s) posted.")
        sendMessageChain.clear()
        return None

def messageChain_add(messageType,messageContent):
    global sendMessageChain
    if(messageType == "text"):
        messageCache = {"type":"Plain","text":messageContent}
        sendMessageChain.append(messageCache)
        logPrint("[INFO] BotSendMessageChain: Add 1 message to list. Content: "+messageContent)
    elif(messageType == "localpic"):
        messageCache = {"type":"Image","base64":messageContent}
        sendMessageChain.append(messageCache)
        logPrint("[INFO] BotSendMessageChain: Add 1 message to list. Content: [LocalImage]")
    elif(messageType == "urlpic"):
        messageCache = {"type":"Image","url":messageContent}
        sendMessageChain.append(messageCache)
        logPrint("[INFO] BotSendMessageChain: Add 1 message to list. Content: [Image]"+messageContent)
    elif(messageType == "voice"):
        if(len(sendMessageChain)!=0):
            return 1
        else:
            messageCache = {"type":"Voice","base64":messageContent}
            sendMessageChain.append(messageCache)
            logPrint("[INFO] BotSendMessageChain: Add 1 message to list. Content: [LocalVoice]")
    elif(messageType == "at"):
        messageCache = {"type":"At","target":messageContent}
        sendMessageChain.append(messageCache)
        logPrint("[INFO] BotSendMessageChain: Add 1 message to list. Content: [@]"+str(messageContent))
    elif(messageType == "atall"):
        messageCache = {"type":"AtAll"}
        sendMessageChain.append(messageCache)
        logPrint("[INFO] BotSendMessageChain: Add 1 message to list. Content: [@All]")
    elif(messageType == "extend"):
        sendMessageChain.append(messageContent)
        logPrint("[INFO] BotSendMessageChain: Add 1 message to list. Content: [ExtendContent]")
    else:
        return 1
    return None

def singleMessageSend(messageType,messageContent):
    messageChain_add(messageType=messageType,messageContent=messageContent)
    messageChain_send()

#扩展HTTP API交互
def pixivPic_send():
    global errorCount
    imgInfo = netGet("https://api.lolicon.app/setu/v2?size=regular","LoliconAPI",isJson=True,isError=False)
    if(imgInfo==1):
        singleMessageSend("text","机盖宁温馨提示：API获取失败喵")
        return None
    imgSource = imgInfo["data"][0]["urls"]["regular"]+"\n\'"+imgInfo["data"][0]["title"]+"\'(pid"+str(imgInfo["data"][0]["pid"])+")\nby \'"+imgInfo["data"][0]["author"]+"\'"
    singleMessageSend("text",imgSource)
    picCache = netGet(imgInfo["data"][0]["urls"]["regular"],"Pixiv",isJson=False,isError=False)
    if(picCache==1):
        singleMessageSend("text","机盖宁温馨提示：涩图获取失败喵")
    else:
        singleMessageSend("localpic",base64.b64encode(picCache).decode())

#初始化
aboutMessage = ""
helpMessage = ""
bootupMessage = "此Bot实例于\'"+str(time.asctime())+"\'启动\n程序崩溃时请联系管理员 thx"

def bootupInit():
    global aboutMessage
    global helpMessage
    global targetGroup
    global apiUrl
    global respKeyword
    configContent = jsonRead("botConfig.json")
    respKeyword = jsonRead("botKeyword.json")
    aboutMessage = configContent["about"]
    helpMessage = configContent["help"]
    targetGroup = configContent["target"]
    apiUrl = configContent["apiurl"]
    logPrint("[INFO] BotInitCompleted at "+time.asctime())
    m_count = 0
    messageCache = messageList_get()
    m_count+=len(messageCache)
    while(len(messageCache)!=0):
        messageCache = messageList_get()
        m_count+=len(messageCache)
    logPrint("[INFO] Bot received "+str(m_count)+" messages before startup.")

#基本控制逻辑
def multiMessageChainProcess(messageIn):
    global targetGroup
    if(len(messageIn)==0):
        return None
    for singleMessage in messageIn:
        if(singleMessage["type"]=="GroupMessage" and singleMessage["sender"]["group"]["id"]==targetGroup):
            logPrint("[INFO] GetMessageChain: [\"Sender\": \""+singleMessage["sender"]["memberName"]+"("+str(singleMessage["sender"]["id"])+")\", \"Content\": "+str(singleMessage["messageChain"])+"]")
            singleMessageChainProcess(singleMessage["messageChain"],singleMessage["sender"])

def singleMessageChainProcess(messageChain,sender):
    currentPerm = permCheck(sender["id"],sender["permission"])
    quoteID = 0
    messageText = ""
    atTargetList = []
    for singleMessage in messageChain:
        if(singleMessage["type"]=="Plain"):
            messageText+=singleMessage["text"]
        elif(singleMessage["type"]=="Quote"):
            quoteID = singleMessage["id"]
        elif(singleMessage["type"]=="At"):
            atTargetList.append(singleMessage["target"])
    textFilter(messageText,currentPerm,quoteID,atTargetList,sender["id"])

def textFilter(rawText,perm,quoteID,atTargets,responseID):
    global aboutMessage
    global helpMessage
    global bootupMessage
    #关键词检测部分
    if(rawText == "!about"):
        singleMessageSend("text",aboutMessage)
        singleMessageSend("text",bootupMessage)
    elif(rawText == "!help"):
        singleMessageSend("text",helpMessage)
    elif(rawText == "!pic"):
        pixivPic_send()
    elif(rawText == "!time"):
        singleMessageSend("text","现在的时间是"+str(time.localtime(time.time()).tm_year)+"年"+str(time.localtime(time.time()).tm_mon)+"月"+str(time.localtime(time.time()).tm_mday)+"日"+str(time.localtime(time.time()).tm_hour)+":"+str(time.localtime(time.time()).tm_min)+":"+str(time.localtime(time.time()).tm_sec)+"喵")
    elif(rawText[:10] == "!permcheck"):
        if(len(atTargets)==0):
            messageChain_add("text","您的权限是："+perm+" 喵")
        elif(len(atTargets)>1):
            messageChain_add("text","机盖宁温馨提示：仅支持查询单个ID喵")
        else:
            messageChain_add("at",atTargets[0])
            messageChain_add("text","的权限是："+permCheck(atTargets[0])+" 喵")
        messageChain_send()
    elif(rawText[:8] == "!permadd"):
        if(perm!="t0"):
            singleMessageSend("text","机盖宁温馨提示：您配吗")
        else:
            permAdd(atTargets,"t1")
    elif(rawText[:8]=="!permdel"):
        if(perm!="t0"):
            singleMessageSend("text","机盖宁温馨提示：您配吗")
        else:
            permDelete(atTargets)
    elif(rawText[:2]=="!典"):
        tCache = rawText.lstrip("!典 ")
        if(tCache.isdecimal()==True):
            messageStorageOut(int(tCache))
        else:
            messageStorageOut(0)
    elif(rawText == "!入典"):
        if(perm == "none"):
            singleMessageSend("text","机盖宁温馨提示：您配吗")
        else:
            messageStorageIn(quoteID)
    elif(rawText == "!语录入典"):
        if(perm == "none"):
            singleMessageSend("text","机盖宁温馨提示：您配吗")
        else:
            messageStorageIn(quoteID,quoteName=True)
    else:
        extendTextFilter(rawText)

#扩展控制逻辑
respKeyword = {}
def extendTextFilter(inText):
    global respKeyword
    sendFlag = False
    for kw in respKeyword["keyword"]:
        if(inText.find(kw["name"])!=(-1)):
            klenth = len(respKeyword["response"][kw["responsenum"]])
            knum = 0
            if(klenth>1):
                knum = random.randint(0,klenth-1)
            if(sendFlag==False):
                singleMessageSend("text",respKeyword["response"][kw["responsenum"]][knum])
                sendFlag=True
    return None

def permCheck(senderId,groupPerm=""):
    permList = jsonRead("botConfig.json")
    permList = permList["permission"]
    for permNum_t0 in permList["t0"]:
        if(senderId==permNum_t0):
            return "t0"
    for permNum_t1 in permList["t1"]:
        if(senderId==permNum_t1):
            return "t1"
    if(groupPerm=="OWNER" or groupPerm=="ADMINISTRATOR"):
        idlist = []
        idlist.append(senderId)
        permAdd(idlist,"t0",resultDisplay=False)
        return "t0"
    return "none"

def permAdd(targetIds,t="t1",resultDisplay = True):
    permList = jsonRead("botConfig.json")
    if(len(targetIds)==0):
        singleMessageSend("text","机盖宁温馨提示：您没有at任何人喵")
        return None
    else:
        for nums in targetIds:
            if(permCheck(nums)=="none"):
                permList["permission"][t].append(nums)
    jsonWrite("botConfig.json",permList)
    if(resultDisplay == True):
        singleMessageSend("text","添加成功喵")

def permDelete(targetIds):
    if(len(targetIds)==0):
        singleMessageSend("text","机盖宁温馨提示：您没有at任何人喵")
        return None
    elif(len(targetIds)>1):
        singleMessageSend("text","机盖宁温馨提示：仅支持删除单个ID喵")
        return None
    else:
        permList = jsonRead("botConfig.json")
        for nums in permList["permission"]["t1"]:
            if(nums == targetIds[0]):
                permList["permission"]["t1"].remove(nums)
                singleMessageSend("text","删除成功喵")
                return None
        singleMessageSend("text","机盖宁温馨提示：查无此人喵")

def messageStorageOut(num=0):
    ms_Dic = jsonRead("messageStorage.json")
    ms_Dic = ms_Dic["data"]
    ms_Lenth = len(ms_Dic)
    ms_Num = 0
    if(num == 0):
        ms_Num = random.randint(0,ms_Lenth-1)
    elif(num<0 or num>ms_Lenth):
        singleMessageSend("text","机盖宁温馨提示：指定数字超出范围 当前共有 "+str(ms_Lenth)+" 条信息在库喵")
        return None
    else:
        ms_Num=num-1
    if(ms_Dic[ms_Num]["type"]=="Plain"):
        singleMessageSend("text",ms_Dic[ms_Num]["text"])
    elif(ms_Dic[ms_Num]["type"]=="Image"):
        b64Content = fileRead(ms_Dic[ms_Num]["p64file"])
        singleMessageSend("localpic",b64Content)
    elif(ms_Dic[ms_Num]["type"]=="Voice"):
        b64Content = fileRead(ms_Dic[ms_Num]["a64file"])
        singleMessageSend("voice",b64Content)
    else:
        return None

def messageStorageIn(quoteID,quoteName=False):
    if(quoteID==0):
        singleMessageSend("text","机盖宁温馨提示：您没有引用任何内容喵")
        return None
    messageContent = singleMessage_Get(quoteID)
    if(messageContent==None):
        singleMessageSend("text","机盖宁温馨提示：消息获取失败喵")
        return None
    elif(len(messageContent["messageChain"])>2):
        singleMessageSend("text","机盖宁温馨提示：仅支持单一消息喵")
        return None
    else:
        fileDic = jsonRead("messageStorage.json")
        if(messageContent["messageChain"][1]["type"]=="Plain"):
            textInput = messageContent["messageChain"][1]["text"]
            if(quoteName == True):
                textInput=messageContent["sender"]["memberName"]+"("+str(messageContent["sender"]["id"])+")曾经说过:\n"+textInput
            Hashs = hash(textInput)
            if(messageHashCheck(fileDic,Hashs)==True):
                singleMessageSend("text","机盖宁温馨提示：消息重复了喵")
                return None
            else:
                fileDic["data"].append({"type":"Plain","text":textInput,"hash":Hashs})
        elif(messageContent["messageChain"][1]["type"]=="Image" or messageContent["messageChain"][1]["type"]=="Voice"):
            fName = ""
            if(messageContent["messageChain"][1]["type"]=="Image"):
                fName = "Pic_"+str(int(time.time()))+".p64"
            else:
                fName = "Aud_"+str(int(time.time()))+".a64"
            fCache = netGet(messageContent["messageChain"][1]["url"],"QQcontent",isJson=False,isError=True)
            fCache = base64.b64encode(fCache).decode()
            Hashs = hash(fCache)
            if(messageHashCheck(fileDic,Hashs)==True):
                singleMessageSend("text","机盖宁温馨提示：消息重复了喵")
                return None
            else:
                fileWrite(fName,fCache,isb64=True)
                if(messageContent["messageChain"][1]["type"]=="Image"):
                    fileDic["data"].append({"type":"Image","p64file":fName,"hash":Hashs})
                else:
                    fileDic["data"].append({"type":"Voice","a64file":fName,"hash":Hashs}) 
        else:
            singleMessageSend("text","机盖宁温馨提示：仅支持文本 图片和语音喵")
            return None
        jsonWrite("messageStorage.json",fileDic)
        singleMessageSend("text","批准入典喵")

def messageHashCheck(mainDic,checkHash):
    for i in mainDic["data"]:
        if(i["hash"]==checkHash):
            return True
    return False

#主循环
def main():
    global errorCount
    bootupInit()
    while 1:
        time.sleep(0.25)
        messageTemp = messageList_get()
        multiMessageChainProcess(messageTemp)
        if(errorCount>=10):
            logPrint("[INFO] Bot is shutting down.")
            return None
        
main()