from google.appengine.api import channel
from django.utils import simplejson as json
import gluon
# add security - check for channel id
@auth.requires_login()
def setFlag():
    db.auth_user[request.vars.userId].update_record(flag=request.vars.flag)
    for i in db.auth_user[request.vars.userId].friends_ids:
        if not db.auth_user[i].offline:
            channel_msg = json.dumps({'type':request.vars.flag,'userId':request.vars.userId})
            channel.send_message(db.auth_user[i].channel_id, channel_msg)
    return request.vars.flag

@auth.requires_login()
def transferVidToks():
    channel_msg = json.dumps({'type':'vidToks','vidTok':request.vars.vidTok,'userId':auth.user.id,'channel_id':auth.user.channel_id})
    channel.send_message(db.auth_user[request.vars.userId].channel_id, channel_msg)
    return True
    
@auth.requires_login()
def changeActualStatus():
    thisUser=db.auth_user[auth.user.id]
    thisUser.update_record(status=request.vars.newStatus)
    for friendId in thisUser.friends_ids:
        friend=db.auth_user[friendId]
        if not friend.offline:
            channel_msg = json.dumps({'type':'actualStatusChange','userId':auth.user.id,'newStatus':request.vars.newStatus})
            channel.send_message(db.auth_user[friendId].channel_id, channel_msg)
    return True

@auth.requires_login()
def addFriend():
    try:
        toUser=db(db.auth_user.email==request.vars.email).select().first()
    except:
        return "nouser"
    if not toUser:
        return "nouser"
    thisUser=db.auth_user[auth.user.id]
    if toUser.id in thisUser.friends_ids:
        return False
    flag1=0
    flag2=0
    pending=thisUser.friendPending_ids
    if toUser.id not in pending :
        flag1=1
        pending.append(toUser.id)
        db.auth_user[auth.user.id].update_record(friendPending_ids=pending)
    
    reqs=toUser.friendReq_ids
    if auth.user.id not in reqs:
        flag2=1
        reqs.append(auth.user.id)
        db(db.auth_user.email==request.vars.email).select().first().update_record(friendReq_ids=reqs)
    if flag1==1 and flag2==1:
        channel_msg = json.dumps({'type':'addFriend','userId':auth.user.id,'name':auth.user.first_name+" "+auth.user.last_name})
        channel.send_message(db.auth_user[toUser.id].channel_id, channel_msg)
    return True

@auth.requires_login()
def decFriendReq():
    toUser=db.auth_user[request.vars.userId]
    thisUser=db.auth_user[auth.user.id]
    flag=request.vars.flag
    
    pending=toUser.friendPending_ids
    if auth.user.id in pending:
        pending.remove(auth.user.id)
        toUser.update_record(friendPending_ids=pending)
    
    if flag=='true':
        toUserFriends=toUser.friends_ids
        if auth.user.id not in toUserFriends:
            toUserFriends.append(auth.user.id)
            toUser.update_record(friends_ids=toUserFriends)

    reqs=thisUser.friendReq_ids
    if int(request.vars.userId) in reqs:
        reqs.remove(int(request.vars.userId))
        thisUser.update_record(friendReq_ids=reqs)
        
    if flag=='true':
        thisUserFriends=thisUser.friends_ids
        if int(request.vars.userId) not in thisUserFriends:
            thisUserFriends.append(int(request.vars.userId))
            thisUser.update_record(friends_ids=thisUserFriends)
        channel_msg = json.dumps({'type':'addedFriend','userId':auth.user.id,'name':thisUser.first_name+" "+thisUser.last_name,'statusFlag':thisUser.flag,'offline':thisUser.offline})
        channel.send_message(toUser.channel_id, channel_msg)
        toUserInfo=json.dumps({'statusFlag':toUser.flag,'offline':toUser.offline})
    return toUserInfo

@auth.requires_login()
def setOffline():
    db.auth_user[auth.user.id].update_record(offline=True)
    for friend_id in db.auth_user[auth.user.id].friends_ids:
        if not db.auth_user[friend_id].offline:
            channel_msg = json.dumps({'type':'offline','userId':auth.user.id})
            channel.send_message(db.auth_user[friend_id].channel_id, channel_msg)
    session.online=False
    redirect(URL(f='user',args='logout',vars={'_next':URL(f='user',args='login')}))

@auth.requires_login()
def index():
    if not session.online:
        db.auth_user[auth.user.id].update_record(offline=False)
        for friend_id in db.auth_user[auth.user.id].friends_ids:
            if not db.auth_user[friend_id].offline:
                channel_msg = json.dumps({'type':db.auth_user[auth.user.id].flag,'userId':auth.user.id})
                channel.send_message(db.auth_user[friend_id].channel_id, channel_msg)
        session.online=True
    nick=auth.user.first_name
    channel_id=auth.user.channel_id
    chat_token = channel.create_channel(channel_id)
    messages=db().select(db.message.ALL)
    friends=[]
    for i in db.auth_user[auth.user.id].friends_ids:
        friends.append(db.auth_user[i])
    friendReqs=db.auth_user[auth.user.id].friendReq_ids
    return dict(nick=nick,channel_id=channel_id,chat_token=chat_token,messages=messages,friends=friends,friendReqs=friendReqs)

@auth.requires_login()
def settings():
    mySettings=db(db.settings.userId==auth.user.id).select().last()
    if not mySettings:
        mySettings=db.settings.insert(userId=auth.user.id)
    
    textMacro=SQLFORM(db.text_replacements)
    imgMacro=SQLFORM(db.image_replacements)
    settingsForm=crud.update(db.settings,mySettings.id,deletable=False)
    
    existingTextMacros=[]
    existingImageMacros=[]
    for i in mySettings.text_replacement_id :
        existingTextMacros.append(crud.update(db.text_replacements,i))
    for i in mySettings.image_replacement_id:
        existingImageMacros.append(crud.update(db.image_replacements,i))
    
    if textMacro.accepts(request.vars,session):
        newTrids=mySettings.text_replacement_id
        newTrids.append(textMacro.vars.id)
        mySettings.update_record(text_replacement_id=newTrids)
        redirect(URL(f='settings'))
    if imgMacro.accepts(request.vars,session):
        newIrids=mySettings.image_replacement_id
        newIrids.append(imgMacro.vars.id)
        mySettings.update_record(image_replacement_id=newIrids)
        redirect(URL(f='settings'))
    if settingsForm.accepts(request.vars,session):
        redirect(URL(f='settings'))
    response.title="Chat Settings"
    return dict(settingsForm=settingsForm,textMacro=textMacro,imgMacro=imgMacro,existingTextMacros=existingTextMacros,existingImageMacros=existingImageMacros)

@auth.requires_login()
def unblockF():
    userId=int(request.vars.userId)
    unblockIds=int(request.vars.unblockIds)
    
    alreadyBlocked=db.auth_user[userId].block_ids
    if unblockIds in alreadyBlocked:
        alreadyBlocked.remove(unblockIds)
    
    db.auth_user[userId].update_record(block_ids=alreadyBlocked)
    return True

@auth.requires_login()
def blockF():
    userId=int(request.vars.userId)
    blockIds=int(request.vars.blockIds)
    
    alreadyBlocked=db.auth_user[userId].block_ids
    if blockIds not in alreadyBlocked:
        alreadyBlocked.append(blockIds)
    
    db.auth_user[userId].update_record(block_ids=alreadyBlocked)
    return True

@auth.requires_login()
def removeF():
    someUser=db.auth_user[request.vars.userId]
    nowFriends=someUser.friends_ids
    print nowFriends, int(request.vars.removeIds)
    if int(request.vars.removeIds) in nowFriends:
        nowFriends.remove(int(request.vars.removeIds))
    someUser.update_record(friends_ids=nowFriends)
    
    removedUser=db.auth_user[request.vars.removeIds]
    hisFriends=removedUser.friends_ids
    if int(request.vars.userId) in hisFriends:
        hisFriends.remove(int(request.vars.userId))
    removedUser.update_record()
    return True

@auth.requires_login()
def manageF():
    thisUser=db.auth_user[auth.user.id]
    friends=thisUser.friends_ids
    blockedF=thisUser.block_ids
    response.title="Manage Friends"
    return dict(friends=friends,blockedF=blockedF)
    
@auth.requires_login()
def messages():
    userId = request.vars.userId
    blockedF=db.auth_user[userId].block_ids
    if auth.user.id in blockedF:
        return "Sorry :( This user has blocked you"
    text = request.vars.text
    mySettings=db(db.settings.userId==auth.user.id).select().last()
    trids=[]
    irids=[]
    newText=""
    if not mySettings:
        mySettings=db.settings.insert(userId=auth.user.id)
    if mySettings:
        for i in mySettings.text_replacement_id:
            trids.append(db.text_replacements[i])
        for i in mySettings.image_replacement_id:
            irids.append(db.image_replacements[i])
        for i in text.split():
            inFlag=0
            for j in trids:
                if i==j.word:
                    inFlag=1
                    newText=newText+j.replace+" "
            for j in irids:
                if i==j.word:
                    inFlag=1
                    newText=newText+"<img src='"+URL(f='download',args=j.replace)+"' alt='"+i+"' style='width:16px;height:16px'/> "
            if inFlag==0:
                newText+=i+" "
    db.history.insert(userIds=str(auth.user.id)+"-"+str(userId),chat=newText)
    outstr="""<div class="message">
    <span>
        """+auth.user.first_name+""" : 
    </span>
    <div>
        &nbsp;"""+newText+"""
    </div>
</div>"""
    if not db.auth_user[userId].offline:
        channel_msg = json.dumps({'type':'chat',"html":outstr,'from':auth.user.id})
        channel.send_message(db.auth_user[userId].channel_id, channel_msg)
    return dict(message=newText)

@auth.requires_login()
def groupMessages():
    userIds = str(request.vars.userIds)
    userIds = userIds.split(',')
    text = request.vars.text
    mySettings=db(db.settings.userId==auth.user.id).select().last()
    trids=[]
    irids=[]
    newText=""
    if not mySettings:
        mySettings=db.settings.insert(userId=auth.user.id)
    if mySettings:
        for i in mySettings.text_replacement_id:
            trids.append(db.text_replacements[i])
        for i in mySettings.image_replacement_id:
            irids.append(db.image_replacements[i])
        for i in text.split():
            inFlag=0
            for j in trids:
                if i==j.word:
                    inFlag=1
                    newText=newText+j.replace+" "
            for j in irids:
                if i==j.word:
                    inFlag=1
                    newText=newText+"<img src='"+URL(f='download',args=j.replace)+"' alt='"+i+"' style='width:16px;height:16px'/> "
            if inFlag==0:
                newText+=i+" "
    outstr="""<div class="message">
    <span>
        """+auth.user.first_name+""" : 
    </span>
    <div>
        &nbsp;"""+newText+"""
    </div>
</div>"""
    for uId in userIds:
        userIdsForThisUser=userIds[:]
        userIdsForThisUser.remove(uId)
        userIdsForThisUser.append(auth.user.id)
        
        userNamesForThisUser=""
        for i in userIdsForThisUser:
            userNamesForThisUser+=db.auth_user[i].first_name+","
        
        if not db.auth_user[uId].offline:
            channel_msg = json.dumps({'type':'groupChat',"html":outstr,'from':auth.user.id,'userIds':userIdsForThisUser,'userNames':userNamesForThisUser})
            channel.send_message(db.auth_user[uId].channel_id, channel_msg)
    return dict(message=newText)

def comp(x,y):
    if x['id']>y['id']:
        return 1
    elif x['id']==y['id']:
        return 0
    else:
        return -1

@auth.requires_login()
def historyF():
    thisUser=db.auth_user[auth.user.id]
    otherUser=db.auth_user[request.vars.friendId]
    
    x=str(auth.user.id)+"-"+str(request.vars.friendId)
    y=str(request.vars.friendId)+"-"+str(auth.user.id)
    iSaid=db(db.history.userIds==x).select()
    heSaid=db(db.history.userIds==y).select()
    
    history=iSaid.as_list()+heSaid.as_list()
    history.sort(comp)
    response.title="Your Chat with "+otherUser.first_name+" "+otherUser.last_name
    return dict(thisUser=thisUser,otherUser=otherUser,history=history)

@auth.requires_login()
def history():
    friendIds=db.auth_user[auth.user.id].friends_ids
    friends=[]
    for i in friendIds:
        friends.append(db.auth_user[i])
    response.title="Chat History"
    return dict(friends=friends)

def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    """
    if auth.user and request.args(0)=='login':
        redirect(URL('index'))
    return dict(form=auth())


def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request,db)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()


@auth.requires_signature()
def data():
    """
    http://..../[app]/default/data/tables
    http://..../[app]/default/data/create/[table]
    http://..../[app]/default/data/read/[table]/[id]
    http://..../[app]/default/data/update/[table]/[id]
    http://..../[app]/default/data/delete/[table]/[id]
    http://..../[app]/default/data/select/[table]
    http://..../[app]/default/data/search/[table]
    but URLs bust be signed, i.e. linked with
      A('table',_href=URL('data/tables',user_signature=True))
    or with the signed load operator
      LOAD('default','data.load',args='tables',ajax=True,user_signature=True)
    """
    return dict(form=crud())
