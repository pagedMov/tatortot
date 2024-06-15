import discord
from discord.ext import commands
import subprocess
import json
import asyncio
import sys
import os

#newline
silent = False
if len(sys.argv) > 1 and sys.argv[1] == "silent": # This will prevent the bot from printing all of the data on the first scrape
    silent = True # useful if you're debugging and don't want to spam the server

with open('creds.json', 'r') as file: # get channel id from credentials file
    creds = json.load(file)
    BOT_TOKEN = creds["BOT_TOKEN"]
    channel_id = creds["channelid"]
    #channel_id = creds["debugid"] # channel i use for debugging

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
known_projects = []

if os.path.exists("./log.txt"): # insert a newline whenever the bot starts, makes the log more readable
    with open("log.txt", "a") as log:
        log.write("\n")

def writelog(string,level):
    levels = {
        "1": "[STATUS] ",
        "2": "[WARNING] ",
        "3": "[ERROR] "
    }
    level = levels[level]
    with open("log.txt", "a") as log:
        log.write(level + string + "\n")
    print(level + string)


def update_projects(new_projects):
    """
    This function updates the list of known projects.

    1. Take a list of projects as an argument
    2. If any of the projects in known_projects are not in new_projects, then remove the old information
    3. If any of the projects in new_projects are not in known_projects, then add the new information
    """
    for project in known_projects:
        if project not in new_projects:
            known_projects.remove(project)
            writelog(f"Removed project {project['name']}", "1")

    for project in new_projects:
        if project not in known_projects:
            known_projects.append(project)
            writelog(f"Added project {project['name']}", "1")


async def read_scrape_output(channel_id):
    """
    This function listens to the scrapetable.py script for the JSON output.

    1. Run scrapetable.py as a subprocess
    2. Connect the bot to the channel at channel_id
    3. Loop, await output from scrapetable.py
    4. When scrapetable.py gives an output, if it is not empty, then process it like this:
        i. initialize an empty string
        ii. iterate through the projects. for each project, if that project's info is in the list of known projects, then skip it
        iii. construct a string using markdown, keeping project info in a code block because it looks nice
        iv. update known_projects with the new info
        v. send the constructed string to the channel
        vi. if there is no new info, just print "no new projects" to the console as stderr debug output
    """
    global silent
    process = await asyncio.create_subprocess_exec(
        'python3', 'scrapetable.py',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    channel = bot.get_channel(channel_id)
    if not channel:
        writelog("No channel found", "3")
        return

    while True:
        output = await process.stdout.readline()
        if output:
            projects_info = json.loads(output.decode().strip())
            projects_str = ""
            if silent:
                update_projects(projects_info) # if silent is True, then update the known_projects list *before* printing the data
                silent = False # then set silent to False. This prevents the bot from printing all of the data on the first run

            for project_info in projects_info:
                found = False
                for dict in known_projects:
                    if project_info["id"] == dict["id"]:
                        found = True
                        break
                if found:
                    continue
                if "Project Codex" in project_info["name"]:
                    await channel.send("@Tators !!! PROJECT CODEX IS BACK !!!")
                projects_str += "```\n"
                projects_str += f"""
Name: {project_info["name"]}\n
Pay: {project_info["pay"]}\n
Tasks: {project_info["numTasks"]}\n
                """
                projects_str += "```\n"
            update_projects(projects_info)
            if projects_str:
                await channel.send("New high-paying projects: \n" + projects_str)
            else:
                writelog("No new projects.", "1")

    rc = await process.wait() # Don't listen to your LSP server's lies; this code is reachable if the script crashes.
    writelog(f'Web scraping process exited with return code {rc}', "3")

@bot.event
async def on_ready():
    """
    This is just the "main" function for the bot

    1. Print the bot's name and ID when it logs in
    2. Create an endless task that writes notifications to the server using output from scrapetable.py
    """
    writelog(f'Logged in as {bot.user.name} ({bot.user.id})', "1")
    bot.loop.create_task(read_scrape_output(channel_id))

@bot.command()
async def getprojects(ctx):
    """
    This is a bot command. You can call !getprojects to run this function from the server.
    It constructs strings the same way that read_scrape_output() does.
    """
    invoker = ctx.author.name
    channel = bot.get_channel(channel_id)
    writelog(f"Command getprojects invoked by {invoker}", "1")
    if not known_projects:
        await channel.send("No high-paying projects currently.")
    log_str = ""
    projects_str = ""
    for project_info in known_projects:
        writelog(f"Sent project: {project_info['name']}", "1")
        projects_str += "```\n"
        projects_str += f"""
Name: {project_info["name"]}\n
Pay: {project_info["pay"]}\n
Tasks: {project_info["numTasks"]}\n
"""
        projects_str += "```\n"

    await channel.send("Current high-paying projects:" + projects_str)


t commit
bot.run(BOT_TOKEN) # This starts the bot
