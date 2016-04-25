import socket
import time
import traceback
import select


IP="192.168.0.100"
PORT=5007

refreshInterval=1.2 #1 minute represents a change of 0.303
lastRefresh=0
data=""
msgType=""
devID=""
message=""
resetCalCheck=True

sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('',PORT))

#Pick up from the last entry number
print("Initiallizing...")
check=open("UDPLog.txt",'a')
check.close()
readFile=open("UDPLog.txt","r")
readLines=readFile.readlines()
readFile.close()
#Error handle for when a file is only 3 lines long
if len(readLines)==0:
    entryNum=0
    print("Blank file found: Added new header")
    log=open("UDPLog.txt","a")
    log.write("#,Timestamp,IP,Type,ID,Value\n") #Log a header
    log.close()
elif len(readLines)==1:
    print("Blank file found: Header exists")
    entryNum=0
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
    pos=firstLine.index(',')
    firstNum=int(firstLine[0:pos])
    pos=lastLine.index(',')
    entryNum=int(lastLine[0:pos])
    #next code introduction, auto archiving for large datasets
    #if lastNum-firstNum>20:
    #    archive=open("UDPLogArchive.txt","a")
    #    read=open("UDPLog.txt","w")    
print("---- Now receiving on IP " + str(IP) + " at port " + str(PORT) + " ----")


def getDevIP(devID):
    log=open("DeviceLog.txt","r")
    lines=log.readlines()
    log.close()
    for line in lines:
        if line[:6]==devID:
            pos=line.index(",",8)
            outIP = line[7:pos]
            break
        else:
            outIP = "No IP"
    return outIP;

def logMsg( toIP, msgType, devID, msg):
    global entryNum
    entryNum = entryNum + 1
    logData=str(entryNum) + "," + time.strftime("%Y-%m-%d")+" "+time.strftime("%H:%M:%S") + "," + toIP + "," + msgType + "," + devID + "," + msg + "\n"
    log=open("UDPLog.txt","a")
    log.write(logData)
    log.close()
    print("Message logged: " + logData[:-1])
    
def sendUDP( toID, msg ):
    toIP=getDevIP(toID)
    if toIP=="No IP":
        print("No IP available for sending to this device: " + toID)
    else:
        sendData=toID + "," + msg
        sendthis=sendData.encode('utf-8') #Changing type
        sock.sendto(sendthis,(toIP,PORT))
        print("Sent message: ", sendData)
        logMsg(toIP,"OUT",toID,msg)
    return;

def logIP( devID, devIP, devDescriptor):
    logDev=devID + "," + devIP + "," + devDescriptor + "," + time.strftime("%Y-%m-%d")+" "+time.strftime("%H:%M:%S") + "\n"
    log=open("DeviceLog.txt","r") #open to read in file contents
    lines=log.readlines() #stores file to memory
    log.close
    lines.append(logDev) #adds the new line
    lines.reverse()
    out=list()
    entries=set()
    for line in lines:
        if line[:6] not in entries:
            out.append(line)
            entries.add(line[:6])
    out.reverse()
    log=open("DeviceLog.txt","w")
    for line in out:
        log.write(line)
    log.close()
    print("IP logged: " + logDev[:-1])
    return;

def refreshRecents():
    log=open("UDPLog.txt","r") #open to read in file contents
    lines=log.readlines() #stores file to memory
    log.close
    lines.reverse()
    out=list()
    entries=set()
    for line in lines:
        logSplit=line.split(",")
        logID=logSplit[4]
        if logSplit[3]=="LOG":
            if logID not in entries:
                out.append(logSplit[1] + "," + logID + "," + logSplit[5])
                entries.add(logID)
    out.reverse()
    log=open("RecentsLog.txt","w")
    for line in out:
        log.write(line)
    log.close()
    print("Recent values file refreshed")

def getLastValue(devID):
    output="Empty"
    log=open("RecentsLog.txt","r") #open to read in file contents
    lines=log.readlines() #stores file to memory
    log.close
    for line in lines:
        logSplit=line.split(",")
        if logSplit[1]==devID:
            output=logSplit[2][:-1];
    return output;
    

#Log what is read and occasionally respond
while True:

    #process incomming message if available
    sockReady=select.select([sock],[],[],0.1) #[True,True]
    if sockReady[0]:
        print("--- Waiting for UDP data")
        data, addr=sock.recvfrom(1024) #Receiving the data from the buffer
        addr=str(addr) #convert to string
        pos2=addr.index("'",3)
        devIP=addr[2:pos2] #trim 4 digit port number
        data=str(data) #change to string
        data=data[2:-1] #strip the b character
        print("Raw incoming message: " + data)

        if refreshInterval<(time.clock()-lastRefresh):
            refreshRecents()
            lastRefresh=time.clock()


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
                print("Scheduled message executed: " + line[20:-1])
                data=line[20:-1]
                devIP=IP
                lines.remove(line)
            #else:
            #    print("This cal event was not triggered:",calSplit[2],calSplit[3][:-1])
        cal=open("CalendarOutput.txt",'w')
        for line in lines:
            cal.write(line)
        cal.close()
    #time.sleep(5) 

    #process data when available
    if data.count(',')==0:
        pass
    elif data.count(',')==2:
        #breaking out the message
        msgType=data.split(",")[0]
        devID=data.split(",")[1]
        message=data.split(",")[2]
        logMsg(devIP,msgType,devID,message)
        data=""
    else:
        print("Invalid message recieved: " + data)
        data=""

    
    #Register oncomming devices
    if msgType=="REG":
        logIP(devID,devIP,message)
        msgType=""

    #Relay the message through
    if msgType=="FWD":
        msgType=""
        if devIP=='No IP':
            print("No registered device found. No action taken.")
        else:
            print("Found registered forwarding device. Forwarding now...")
            sendUDP(devID,message)

    if msgType=="LOG":
        msgType=""
        if devID=="BUT002":
            sendUDP("LED002",message)
        if devID=="CMD003": #weather query message
            sendData=time.strftime("%H:%M")+","+getLastValue("TEM001")+","+getLastValue("TEM002")+","+getLastValue("HUM001")+","+getLastValue("HUM002") #Contstructs the data for sending to android
            print("Just sent weather: " + sendData)
            sendData=sendData.encode('utf-8') #Changing type
            sock.sendto(sendData,(devIP,PORT)) #echo weather data to client
            devID=""

        if message=="all off":
            sendUDP("LED001","off")
            sendUDP("LED002","off")
            sendUDP("LED003","off")
            sendUDP("LED004","off")
            sendUDP("RET003","instant off")


    
    
