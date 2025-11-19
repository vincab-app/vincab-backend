from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

def generate_email_verification_token(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return uid, token

# email
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def send_reset_email(email, token):
    reset_link = f"http://192.168.100.5:8000/reset-password/{token}"  # update with frontend URL

    subject = "Reset Your VinCab Password"
    from_email = settings.DEFAULT_FROM_EMAIL
    to = [email]

    text_content = f"Click the link to reset your password: {reset_link}"
    html_content = render_to_string("reset_email.html", {"reset_link": reset_link})

    msg = EmailMultiAlternatives(subject, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()
