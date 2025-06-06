import os
import re
import random
import logging
import time
import sqlite3
import calendar

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from typing import List, Tuple, Any


# Configuration
EMOJI = os.getenv("EMOJI", "carrot")
PLURAL = os.getenv("PLURAL", "carrots")
LIMIT = int(os.getenv("LIMIT", "-1"))
PER_USER_LIMIT = int(os.getenv("PER_USER_LIMIT", "-1"))
SLACK_TOKEN = os.getenv("SLACKTOKEN")
MYSQLPASS = os.getenv("MYSQLPASS")
DB_PATH = os.getenv("DB_PATH", "kudos.db")

KUDOS_RESPONSE = [":carrot: Nice!", ":carrot: Well done!"]
HELP_RESPONSE = ["Need help? Just ask!"]
SELF_RESPONSE = ["No patting yourself on the back!"]

# Initializes your app with your bot token and socket mode handler
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

def help(channel):

def get_most_recv(month_str):
  print(f"get_most_recv called with month_str:", month_str)
  if not month_str:
    month_str = time.strftime("%B")  # Default to current month

  try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    month_num = time.strptime(month_str, "%B").tm_mon

    # Leaderboard query: top 10 recipients for the given month in the last 12 months
    query = (
              f"SELECT recipient, COUNT(DISTINCT id) FROM kudos_log "
              f"WHERE strftime('%m', timestamp) = '{month_num:02d}' "
              f"AND timestamp >= date('now', '-12 months') "
              f"GROUP BY recipient ORDER BY COUNT(DISTINCT id) DESC LIMIT 10"
    )
    print(f"Executing query: {query}")
    cursor.execute(query)
    rows = cursor.fetchall()

    leaders = []
    for row in rows:
      print(f"Row: {row}")
      leaders.append({
        "recipient": row[0],
        "carrots": row[1]
      })

    cursor.close()
    conn.close()
    return leaders
  except Exception as e:
    return [], e

def store_kudos(sender, recipients, count):
  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()

  #Ensure table exists
  cursor.execute('''
  CREATE TABLE IF NOT EXISTS kudos_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sender TEXT NOT NULL,
      recipient TEXT NOT NULL,
      count INTEGER NOT NULL,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
  )
  ''')
  for _ in range(count):
    for recipient in recipients:
      cursor.execute("INSERT INTO kudos_log (sender, recipient, count) VALUES (?, ?, ?)", (sender, recipient, count))

  conn.commit()
  cursor.close()
  conn.close()

def get_stats(user, month_str):
  conn = sqlite3.connect(DB_PATH)
  cursor = conn.cursor()
  # SQLite does not have MONTHNAME, so use strftime('%m', timestamp)
  cursor.execute("SELECT COUNT(sender) FROM kudos_log WHERE strftime('%m', timestamp) = ? AND sender = ?", (time.strftime("%m"), user))
  sent = cursor.fetchone()[0]
  cursor.execute("SELECT COUNT(recipient) FROM kudos_log WHERE strftime('%m', timestamp) = ? AND recipient = ?", (time.strftime("%m"), user))

  received = cursor.fetchone()[0]
  cursor.close()
  conn.close()
  return sent, received

def verify_recipients(recipients, sender_id, bot_user_id):
  verified = []
  for recipient in recipients:
    recipient = recipient.replace("@", "")
    if recipient == sender_id:
      raise Exception(random.choice(SELF_RESPONSE))
    if recipient == bot_user_id:
      raise Exception("PLEASE DO NOT FEED THE BOT")
    # Optionally, check if user exists via Slack API
    verified.append(recipient)
  return verified

@app.message(":broccoli:")
def message_hello(message, say):
  say(f"Broccoli is not allowed here, <@{message['user']}>! :broccoli:")

@app.message()
def message_default(client, message, say):
    bot_id = client.auth_test()["user_id"]
    channel = message.get("channel", "")
    #say(f"Message: {bot_id} is in {channel}")

    if message['user'] == bot_id:
        say("I don't talk to myself, <@{message['user']}>!")
        return

    carrots = re.findall(r":carrot:", message['text'])
    recipients = re.findall(r"@([A-Za-z][A-Za-z0-9-_]+)", message['text'])
    at_cmd = re.match(f"^<@{bot_id}> *(.*)$", message['text'])

    if carrots and recipients:
      try:
        verified = verify_recipients(recipients, message['user'], bot_id)
        #say(f"Verified recipients: {verified}")
      except Exception as e:
        say(f"{e}")
        return

      have_budget = True
      if LIMIT != -1:
        sent, _ = get_stats(message['user'], time.strftime("%B"))
        if sent + (len(carrots) * len(verified)) > LIMIT:
          have_budget = False

      if PER_USER_LIMIT != -1 and len(carrots) > PER_USER_LIMIT:
        have_budget = False

      if have_budget:
        store_kudos(message['user'], verified, len(carrots))
        bot_resp = random.choice(KUDOS_RESPONSE)
        bot_resp += " " + " ".join([f":{EMOJI}:" for _ in range(len(carrots) * len(verified))])
        bot_resp += " :heart:"
        client.chat_postEphemeral(channel=message['channel'], user=message['user'], text=bot_resp)
      else:
        say(f"Sorry, you can't send more than {LIMIT} {PLURAL} per month.")

    elif at_cmd:
      cmd_str = at_cmd.group(1)
      if cmd_str == "me":
        sent, received = get_stats(message['user'], time.strftime("%B"))
        resp = f"In {time.strftime('%B')}, you have given {sent} {PLURAL} and received {received}."
        client.chat_postEphemeral(channel=message['channel'], user=message['user'], text=resp)
      elif cmd_str.startswith("ladder") or any(month.lower() in cmd_str.lower() for month in calendar.month_name if month):
        month_found = None
        for month in calendar.month_name[1:]:
          if month.lower() in cmd_str.lower():
            month_found = month
            print(f"Found month: {month_found}")
            break

        month_str = time.strftime("%m") if not month_found else time.strptime(month_found, "%B").tm_mon
        month_str = f"{int(month_str):02d}"

        # Implement leaderboard logic here
        # client.chat_postMessage(channel=message['channel'], text="Leaderboard feature not implemented.")
        leaders = get_most_recv(month_found)
        if leaders:
          leaderboard_msg = "*Leaderboard:*\n"
          for leader in leaders:
            leaderboard_msg += f"<@{leader['recipient']}>: {leader['carrots']} {PLURAL}\n"
          client.chat_postMessage(channel=message['channel'], text=leaderboard_msg)
        else:
          client.chat_postMessage(channel=message['channel'], text="No kudos received this month yet.")
      else:
        help_msg = (
          f"*Send {PLURAL} to your friends:*\n"
          f">Hey @shrek, I like you, have a :{EMOJI}:\n"
          f">:{EMOJI}: @shrek @fiona\n"
          f">I like that @boulder, it's a nice boulder :{EMOJI}: :{EMOJI}:\n"
          f"*Other stuff:*\n"
          f">`@bot me` Find out how many :{EMOJI}: you have\n"
          f">`@bot ladder [month]` Find out who has the most :{EMOJI}:\n"
          f">`@bot help` Print this message\n"
          f"{random.choice(HELP_RESPONSE)}"
        )
        client.chat_postMessage(channel=message['channel'], user=message['user'], text=help_msg)
      match cmd_str:
        case "help":
          help_msg = (
            f"*Send {PLURAL} to your friends:*\n"
            f">Hey @shrek, I like you, have a :{EMOJI}:\n"
            f">:{EMOJI}: @shrek @fiona\n"
            f">I like that @boulder, it's a nice boulder :{EMOJI}: :{EMOJI}:\n"
            f"*Other stuff:*\n"
            f">`@bot me` Find out how many :{EMOJI}: you have\n"
            f">`@bot ladder [month]` Find out who has the most :{EMOJI}:\n"
            f">`@bot help` Print this message\n"
            f"{random.choice(HELP_RESPONSE)}"
          )
          client.chat_postMessage(channel=message['channel'], user=message['user'], text=help_msg)
        case _:
          client.chat_postEphemeral(channel=message['channel'], user=message['user'], text="Unknown command. Type `@bot help` for assistance.")

# Start the app
if __name__ == "__main__":
  SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
