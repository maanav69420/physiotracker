def timenow():
    from datetime import datetime, timedelta
    now = datetime.now()
    curr_time = now.strftime("%H:%M")
    
    return curr_time


def get_otp():
    from password import generate
    get_otp = generate()
    return get_otp

def username(to_):
    user = to_.split("@")
    
    return user[0]


def get_content(to_, subject="Inventory Access"):
    curr_time = timenow()
    otp = get_otp()
    user = username(to_)
    print()

    content = f'''Hello {user}, Thanks for using our service.\nThis automated email was sent in {curr_time}. To access the Manager, enter the following OTP:\t {otp}'''
    content = "Subject:{}\n\n{}".format(subject, content)

    return content , otp








