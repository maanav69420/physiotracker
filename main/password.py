def chars():
    alpha = 'abcdefghijklmnopqrstuvwxyz'
    alpha = alpha + alpha.upper()
    num = '1234567890'

    return [alpha , num]


def generate():
    import random 

    avil_char = chars()   
    
    keys = []
    key_len = random.randint(4 , 8) 
    
    while len(keys) != key_len:
        char = ''

        for i in range(4):
            type_ = random.choice(avil_char)
            elm = random.choice(type_)

            char += elm
            
        keys += [char]
            
    keys = '-'.join(keys)

    return keys



