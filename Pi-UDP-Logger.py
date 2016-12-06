import socket, os, time, select

#Global variables
PORT=5007
IP=""
sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('',PORT))
entryNum=0
resetCalCheck=True

def getLocalIP():
    gw = os.popen("ip -4 route show default").read().split()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((gw[2], 0))
    ipAddr = s.getsockname()[0]
    print("Local IP:",ipAddr)
    return ipAddr;

def setupLog():
    global entryNum
    global IP
    print("Initiallizing...")
    IP=getLocalIP()
    readFile=open("UDPLog.txt","a") #create file if it doesn't exist
    readFile.close()
    readFile=open("UDPLog.txt","r")
    readLines=readFile.readlines()
    readFile.close()
    if len(readLines)==0:
        log=open("UDPLog.txt","a")
        log.write("#,Timestamp,Type,ID,Value\n") #Log a header
        log.close()
        print("Blank file found: Added new header")
    elif len(readLines)==1:
        print("Blank file found: Header exists")
    else:
        if len(readLines)==2:
            lastLine=readLines[1]
            firstLine=readLines[1]
        elif len(readLines)==3:
            lastLine=readLines[2]
            firstLine=readLines[1]
        else:
            lastLine=readLines[-1]
            firstLine=readLines[1]
        print("First line stored: " + firstLine[:-1])
        print("Last line stored: " + lastLine)
        pos=lastLine.index(',')
        entryNum=int(lastLine[0:pos])
    print("---- Now receiving on IP " + str(IP) + " at port " + str(PORT) + " ----")

def waitForMessage(): #Primes a message if available
    global sock
    sockReady=select.select([sock],[],[],0.1) #[True,True]
    if sockReady[0]:
        print("")
        print("--- Socket received data")
        message=getMessage()
    else:
        message=""
    return message;

def getMessage():
    global sock
    data, addr=sock.recvfrom(1024) #Receiving the data from the buffer
    addr=str(addr) #convert to string
    pos2=addr.index("'",3)
    devIP=addr[2:pos2] #trim 4 digit port number
    data=str(data) #change to string
    message=devIP+','+data[2:-1] #strip the b character
    print("Raw incoming message:",data)
    print("Output:",message)
    return message;

def scheduledEventGet():
    global resetCalCheck
    global IP
    message=""
    if int(time.strftime('%-S'))%25==0:
        resetCalCheck=True
    if int(time.strftime('%-S'))%26==0 and resetCalCheck==True: #trigger every remainder minutes
        resetCalCheck=False
        cal=open("CalendarOutput.txt",'r')
        lines=cal.readlines()
        cal.close
        for line in lines:
            calSplit=line.split(',')
            if calSplit[0][:-3]==time.strftime('%Y-%m-%d %H:%M'):
                resetCalCheck=True
                lines.remove(line)
                message=IP+','+line[20:-1]
                print("Scheduled message returned:",message)
                break
        cal=open("CalendarOutput.txt",'w')
        for line in lines:
            cal.write(line)
        cal.close()
    return message;

def processMessage(data):
    #Split the message
    msgType=""
    if data.count(',')==0:
        pass
    elif data.count(',')==3: #breaking out the message
        dataSplit=data.split(",") #form at is {IP,type,ID,message}
        msgIP=dataSplit[0]
        msgType=dataSplit[1]
        msgID=dataSplit[2]
        msg=dataSplit[3]
        logMsg(msgType,msgID,msg)
    else:
        print("Invalid message recieved: " + data)
    #Take action on the messages
    if msgType=="FWD":
        if getIpFromId(msgID)=="":
            print("No registered device found. No action taken.")
        else:
            print("Found registered forwarding device. Forwarding now...")
            sendUdp(msgID,msg)      
    elif msgType=="LOG":
        logRecent(msgID,msg)
        if msgID=="BUT001": #forward button pushes
            sendUdp("LED001",msg)
        if msgID=="BUT008": #route button pushes based on value
            if msg=="press":
                sendUdp("LED001","toggle")
            elif msg=="longPress":
                sendUdp("LED002","100")
                sendUdp("LED003","100")
            elif msg=="longestPress":
                allOff()
        if msgID=="BUT009": #route button pushes based on value
            if msg=="press":
                sendUdp("LED001","toggle")
            elif msg=="longPress":
                sendUdp("LED001","100")
            elif msg=="longestPress":
                allOff()
        if msgID=="BUT010": #route button pushes based on value
            if msg=="press":
                sendUdp("LED002","toggle")
                sendUdp("LED003","toggle")
            elif msg=="longPress":
                sendUdp("LED002","100")
                sendUdp("LED003","100")
            elif msg=="longestPress":
                allOff()
        if msgID=="BUT002": #forward button pushes
            sendUdp("LED002",msg)
            sendUdp("LED003",msg)
        if msgID=="BUT005": #forward button pushes
            sendUdp("LED005",msg)
        if msgID=="BUT015": #forward button pushes
            sendUdp("LED015",msg)
        if msgID=="CMD003": #weather query message
            serveWeatherInfo(msgIP)
        if (msgID=="MOB001" or msgID=="MOB002") and msg=="online" and float(time.strftime('%H'))>17: #turn light on if you arrive home after 7pm
            sendUdp("LED005","timer600 100")
            sendUdp("LED001","timer380 100")
            sendUdp("LED003","timer380 100")
        if msg=="all off":
            allOff()
    elif msgType=="REG":
        regDevice(msgID,msgIP,msg)
        
            
def serveWeatherInfo(devIP):
    global sock
    sendData=time.strftime("%H:%M")+","+getLastValue("TEM001")+","+getLastValue("TEM002")+","+getLastValue("HUM001")+","+getLastValue("HUM002") #Contstructs the data for sending to android
    sendData=sendData.encode('utf-8') #Changing type
    sock.sendto(sendData,(devIP,PORT)) #echo weather data to client
    print("Just sent weather: ", sendData)

def sendUdp(toID,msg):
    global sock
    toIP=getIpFromId(toID)
    if toIP=="":
        print("No IP available for sending to",toID)
    else:
        sendData=toID + "," + msg
        sendthis=sendData.encode('utf-8') #Changing type
        sock.sendto(sendthis,(toIP,PORT))
        print("-- Sent message:", sendData)
        logMsg("OUT",toID,msg)
        
def getLastValue(devID):
    output="Empty"
    log=open("DeviceLog.txt","r") #open to read in file contents
    lines=log.readlines() #stores file to memory
    log.close
    for line in lines:
        logSplit=line.split(",")
        if logSplit[0]==devID:
            output=logSplit[5];
    return output;

def getLastValueTime(devID):
    output="Empty"
    log=open("DeviceLog.txt","r") #open to read in file contents
    lines=log.readlines() #stores file to memory
    log.close
    for line in lines:
        logSplit=line.split(",")
        if logSplit[0]==devID:
            output=logSplit[6][:-1];
    return output;

def allOff(): #consider using a file with devIDs for this instead of DeviceLog
    log=open("DeviceLog.txt","r")
    lines=log.readlines()
    log.close()
    for line in lines:
        logSplit=line.split(",")
        sendUdp(logSplit[0],"off")
                   
def getIpFromId(devID):
    log=open("DeviceLog.txt","r")
    lines=log.readlines()
    log.close()
    outIP = "" #No IP by default
    for line in lines:
        if line[:6]==devID:
            pos=line.index(",",8)
            outIP = line[7:pos]
            break
    return outIP;


def logMsg(msgType,devID,msg):
    global entryNum
    entryNum = entryNum + 1
    logData=str(entryNum) + "," + time.strftime("%Y-%m-%d")+" "+time.strftime("%H:%M:%S") + "," + msgType + "," + devID + "," + msg + "\n"
    log=open("UDPLog.txt","a")
    log.write(logData)
    log.close()
    print("Message logged: " + logData[:-1])

def logRecent(devID,value):
    log=open("DeviceLog.txt","r") #open to read in file contents
    lines=log.readlines() #stores file to memory
    log.close
    for i in range(0,len(lines)):
        logSplit=lines[i].split(",")
        if logSplit[0]==devID:
            lines[i]=logSplit[0]+','+logSplit[1]+','+logSplit[2]+','+logSplit[3]+','+logSplit[4]+','+value+','+time.strftime("%Y-%m-%d")+' '+time.strftime("%H:%M:%S") + '\n'
            print("Updated a registered device's recent state:", logSplit[0])
    log=open("DeviceLog.txt","w")
    for line in lines:
        log.write(line)
    log.close()

def regDevice(msgID,msgIP,msg):
    log=open("DeviceLog.txt","r") #open to read in file contents
    lines=log.readlines() #stores file to memory
    log.close
    noMatch = True
    for i in range(0,len(lines)):
        logSplit=lines[i].split(",")
        if logSplit[0]==msgID:
            lines[i]=msgID+','+msgIP+','+msg+','+'No mac'+','+'online'+','+msg+','+time.strftime("%Y-%m-%d")+' '+time.strftime("%H:%M:%S") + '\n'
            print("Updated a registered device's registration state:", logSplit[0])
            noMatch = False
    log=open("DeviceLog.txt","w")
    for line in lines:
        log.write(line)
    if noMatch:
        log.write(msgID+','+msgIP+','+msg+','+'No mac'+','+'online'+','+msg+','+time.strftime("%Y-%m-%d")+' '+time.strftime("%H:%M:%S") + '\n')
        print("Logged a new unique device:", msgID)
    log.close()


#Log what is read and occasionally respond
setupLog()
while True:
    msgData=waitForMessage()
    if msgData=="":
        msgData=scheduledEventGet()

    #process data when available
    if msgData!="":
        processMessage(msgData)


    
    
