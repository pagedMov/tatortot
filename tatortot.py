import discord
from discord.ext import commands
import subprocess
import json
import asyncio

with open('creds.json', 'r') as file: # get channel id from credentials file
    creds = json.load(file)
    BOT_TOKEN = creds["BOT_TOKEN"]
    channel_id = creds["channelid"]
    #channel_id = creds["debugid"] # channel i use for debugging

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
known_projects = []

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

    for project in new_projects:
        if project not in known_projects:
            known_projects.append(project)


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
    process = await asyncio.create_subprocess_exec(
        'python', 'scrapetable.py',
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    channel = bot.get_channel(channel_id)
    if not channel:
        print("No channel found")
        return

    while True:
        output = await process.stdout.readline()
        if output:
            projects_info = json.loads(output.decode().strip())
            projects_str = ""
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
            print(projects_str)
            update_projects(projects_info)
            if projects_str:
                await channel.send("New high-paying projects: \n" + projects_str)
            else:
                print("no new projects")

    rc = await process.wait() # Don't listen to your LSP server's lies; this code is reachable if the script crashes.
    print(f'Web scraping process exited with return code {rc}')

@bot.event
async def on_ready():
    """
    This is just the "main" function for the bot

    1. Print the bot's name and ID when it logs in
    2. Create an endless task that writes notifications to the server using output from scrapetable.py
    """
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    bot.loop.create_task(read_scrape_output(channel_id))

@bot.command()
async def getprojects(ctx):
    """
    This is a bot command. You can call !getprojects to run this function from the server.
    It constructs strings the same way that read_scrape_output() does.
    """
    channel = bot.get_channel(channel_id)
    if not known_projects:
        await channel.send("No high-paying projects currently.")
    projects_str = ""
    for project_info in known_projects:
        projects_str += "```\n"
        projects_str += f"""
Name: {project_info["name"]}\n
Pay: {project_info["pay"]}\n
Tasks: {project_info["numTasks"]}\n
"""
        projects_str += "```\n"

    await channel.send("Current high-paying projects:" + projects_str)


bot.run(BOT_TOKEN) # This starts the bot
