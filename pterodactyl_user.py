from pydactyl import PterodactylClient

class PterodactylUser:
    def __init__(self, panelURL, pterodactylAPI):
        self.api = PterodactylClient(panelURL, pterodactylAPI)

    # username must be unique
    # this appends an number if a user already exists
    def validateUsername(self, uuid, username):
        postfix = 0
        while len(self.api.user.list_users(username=username + str(postfix if postfix > 0 else ""))) != 0 and len(self.api.user.list_users(external_id=uuid, username=username)) == 0:
            postfix += 1
        return username + str(postfix if postfix > 0 else "")

    # email must be unique
    # this uses a generated email if email already exists
    def validateUserEmail(self, uuid, email):
        if len(self.api.user.list_users(email=email)) != 0 and len(self.api.user.list_users(external_id=uuid, email=email)) == 0:
            email = uuid + "@example.com"
        return email

    def createUser(self, uuid, email, username, name, password, isSuperUser):
        username = self.validateUsername(uuid, username)
        email = self.validateUserEmail(uuid, email)
        self.api.user.create_user(username=username, email=email, first_name=name, last_name="-", external_id=uuid, password=password, root_admin=isSuperUser)

    # Creates and Updates users
    # uuid: same as authentik uuid
    # email: same as authentik email
    # username: same as authentik username
    # name: same as authentik name 
    # pwChange: set to true if password has changed -> will update password stored in pterodactyl
    def createOrUpdate(self, uuid, email, username, name, password, isSuperUser, pwChange = False):
        uuid = str(uuid) # must be string
        users = self.api.user.list_users(external_id=uuid)

        if len(users) == 1:
            # check if username or email has changed in authentik
            if users[0]["attributes"]['username'] == username and users[0]["attributes"]['email'] == email and users[0]["attributes"]['first_name'] == name and users[0]["attributes"]['root_admin'] == isSuperUser and not pwChange:
                return # user has no changes in authentik
            if users[0]["attributes"]['username'] != email:
                username = self.validateUsername(uuid, username) # username has changed -> check if its already taken and adjust accordingly
            if users[0]["attributes"]['email'] != email:
                email = self.validateUserEmail(uuid, email) # email has changed -> check if its already taken and adjust accordingly

            self.api.user.edit_user(user_id=users[0]["attributes"]['id'], username=username, email=email, first_name=name, last_name="-", external_id=uuid, password=password, root_admin=isSuperUser)
            return
        self.createUser(uuid, email, username, name, password, isSuperUser)
