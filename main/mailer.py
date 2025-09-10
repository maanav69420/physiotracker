from body import get_content
import smtplib as smt
import os

def message(to_):
    text, otp = get_content(to_)
    return text, otp
    

def send_mail(from_, p_word):
    print(f"\nsender:\t{from_}\np_word:\t{p_word}")

    to_ = input("SEND EMAIL TO:\t")

    server = smt.SMTP("smtp.gmail.com", 587)
    server.starttls()

    server.login(from_, p_word)

    text, otp = message(to_)

    server.sendmail(from_, to_, text)

    print("Your Email Has been Successfully sent !!!")
    server.quit()

    return None


def sender():
    sender = os.environ.get('GET_SENDER')
    passkey = os.environ.get('GET_PASSKEY')
       
    return sender, passkey

s, p = sender()
