from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import logging
import smtplib
import ssl
from string import Template
from utils.misc import round_price


class Notifier(object):
    def __init__(self, cfg):

        self.smtp_server = cfg['SMTP_SERVER']
        self.sent_from = cfg['EMAIL_ADDRESS_FROM']
        self.to = cfg['EMAIL_ADDRESS_TO']
        self.password = cfg['EMAIL_PASSWORD']
        self.port = 465  # For SSL

        self.exchage = cfg['EXCHANGE'].lower()

        if cfg['TEST']:
            self.exchage += ' (test mode)'

    def info(self, info):
        with open('utils/mail_template/info.html', 'r', encoding='utf-8') as file:
            body = file.read()

        body = Template(body)
        body = body.substitute(info=info,
                               exchange=self.exchage)

        subject = f'DCA: info'

        self.send(subject, body)

    def success(self,
                df,
                cycle,
                next_purchase,
                bought_on,
                pairing,
                stats,
                extra):

        coin = df['coin'][0]

        if 'N.A.' in df['fee'].tolist():
            fee_currency = ''
            fee_rate = ''
            fee = df['fee'][0]
        else:
            fee_currency = df['fee currency'][0]
            fee = round_price(df['fee'][0])
            if 'N.A.' in df['fee rate'].tolist():
                fee_rate = ''
            else:
                fee_rate = "(" + round_price(df['fee rate'][0]*100) + " %)"

        with open('utils/mail_template/success.html', 'r', encoding='utf-8') as file:
            body = file.read()

        body = Template(body)
        body = body.substitute(coin=coin,
                               exchange=self.exchage,
                               cycle=cycle,
                               bought_on=bought_on,
                               next_purchase=next_purchase,
                               filled=df['filled'][0],
                               price=df['price'][0],
                               pairing=pairing,
                               cost=df['cost'][0],
                               fee=fee,
                               fee_currency=fee_currency,
                               fee_rate=fee_rate,
                               total_asset=round_price(stats['Quantity']),
                               avg_price=round_price(stats['AvgPrice']),
                               N=int(stats['N']),
                               total_cost=round_price(stats['TotalCost']),
                               gain=round_price(stats['ROI']),
                               ROI=round_price(stats['ROI%']),
                               extra=extra)

        # Attach graph
        graph_path = 'trades/graph_' + coin + '.png'
        with open(graph_path, 'rb') as img:
            msgimg = MIMEImage(img.read())
        msgimg.add_header('Content-ID', '<graph>')
        # replace src image with src="cid:graph"

        subject = f'DCA: {coin} purchase complete'

        self.send(subject, body, msgimg)

    def warning_funds(self,
                      coin,
                      next_purchase,
                      pairing,
                      cost,
                      balance):

        with open('utils/mail_template/insufficientFundsWarning.html', 'r', encoding='utf-8') as file:
            body = file.read()

        body = Template(body)
        body = body.substitute(coin=coin,
                               exchange=self.exchage,
                               cost=cost,
                               pairing=pairing,
                               balance=balance,
                               next_purchase=next_purchase)

        subject = f'DCA: {coin} warning'

        self.send(subject,body)

    def error(self,
              coin,
              retry_dict,
              error):
        """These errors are not critical and should be recoverable"""
        with open('utils/mail_template/error.html', 'r', encoding='utf-8') as file:
            body = file.read()

        error_type = type(error).__name__

        retry_time = retry_dict[1]
        attempts = retry_dict[0]

        body = Template(body)
        body = body.substitute(coin=coin,
                               exchange=self.exchage,
                               error_type=error_type,
                               error=str(error),
                               retry_time=retry_time,
                               attempts=attempts)

        subject = f'DCA: {coin} purchase failed'

        self.send(subject, body)

    def critical(self,
                 error,
                 when):
        """These errors are critical and the program is terminated after sending one of these"""

        with open('utils/mail_template/critical.html', 'r', encoding='utf-8') as file:
            body = file.read()

        error_type = type(error).__name__

        body = Template(body)
        body = body.substitute(when=when,
                               exchange=self.exchage,
                               error_type=error_type,
                               error=str(error))

        subject = f'DCA: Critical Error'

        self.send(subject, body)

    def send(self, subject, body, img=None):

        # Create message container - the correct MIME type is multipart/alternative here!
        msg = MIMEMultipart('alternative')
        msg['subject'] = subject
        msg['To'] = self.to
        msg['From'] = self.sent_from
        msg.preamble = """
        Your mail reader does not support the report format.
        """

        # Record the MIME type text/html.
        html_body = MIMEText(body, 'html')

        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        msg.attach(html_body)

        if img:
            msg.attach(img)

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_server, self.port, context=context) as server:
                server.login(self.sent_from, self.password)
                server.sendmail(self.sent_from, self.to, msg.as_string())

        except Exception as e:
            logging.warning("SEND MAIL " + type(e).__name__ + ' ' + str(e))
