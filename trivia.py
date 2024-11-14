import discord
from openai import OpenAI
import asyncio
import time
import logging
import random
import json
from datetime import datetime, timedelta
from collections import defaultdict

from apes import get_thread_option

opclient = OpenAI(
)
from apes_assisstant import ASSISSTANT_ID
Discord_BOT_API_KEY="YOUR DISCORD KEY"

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)
class MovieTriviaSystem:
    def __init__(self):

        self.trivia_questions = [
            {
                "question": "Which movie features a character saying 'Here's looking at you, kid'?",
                "options": ["Casablanca", "Gone with the Wind", "Citizen Kane", "The Maltese Falcon"],
                "correct_answer": "Casablanca",
                "difficulty": "medium"
            },
            {
                "question": "Who directed 'Jurassic Park'?",
                "options": ["Steven Spielberg", "George Lucas", "James Cameron", "Robert Zemeckis"],
                "correct_answer": "Steven Spielberg",
                "difficulty": "easy"
            },

        ]

        self.flashcards = [
            {
                "front": "This 1994 film follows a man waiting on a bench, telling his life story.",
                "back": "Forrest Gump",
                "category": "Classic Movies"
            },
            {
                "front": "This director is known for films like 'Pulp Fiction' and 'Kill Bill'.",
                "back": "Quentin Tarantino",
                "category": "Directors"
            }
        ]

        self.user_scores = defaultdict(int)
        self.active_games = {}
        self.streak_counts = defaultdict(int)

    def get_random_question(self):
        return random.choice(self.trivia_questions)

    def get_random_flashcard(self):
        return random.choice(self.flashcards)

    def update_score(self, user_id, points):
        self.user_scores[user_id] += points
        return self.user_scores[user_id]

    def get_leaderboard(self):
        return sorted(self.user_scores.items(), key=lambda x: x[1], reverse=True)


class MovieBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trivia_system = MovieTriviaSystem()
        self.opclient = OpenAI()
        self.assistant_id = ASSISSTANT_ID
        self.thread_id = None


    async def get_thread_option(self):
        if self.thread_id:
            return self.thread_id
        thread = self.opclient.beta.threads.create(
            messages=[{'role': 'user', 'content': "Start Conversation"}]
        )
        self.thread_id = thread.id
        return self.thread_id

    @client.event
    async def on_message(message):
        global thread_id

        if message.author.bot:
            return

        if isinstance(message.channel, discord.DMChannel):

            user_message = message.content.replace(f"<@{client.user.id}>", "").strip()
            user = message.author
            await user.send(f"Hi {user.name}")

            response_message = await user.send("...")

            thread_id = await get_thread_option()

            prompts = opclient.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_message
            )

            # Running Assisstant
            run = opclient.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISSTANT_ID
            )

            while True:
                try:
                    run = opclient.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                    if run.completed_at:
                        messages = opclient.beta.threads.messages.list(
                            thread_id=thread_id
                        )
                        last_message = messages.data[0]
                        response = last_message.content[0].text.value
                        await response_message.edit(content=response)
                        break
                except Exception as e:
                    logging.error(f"Error occured while retreiving the data : {e}")
                    break
                await asyncio.sleep(1)
    async def create_trivia_embed(self, question_data):
        embed = discord.Embed(
            title="🎬 Movie Trivia",
            description=question_data["question"],
            color=discord.Color.blue()
        )

        for i, option in enumerate(question_data["options"]):
            embed.add_field(
                name=f"Option {i + 1}",
                value=option,
                inline=False
            )

        embed.set_footer(text="Reply with the number of your answer (1-4)")
        return embed



    async def process_trivia_answer(self, message, question_data):
        try:
            answer_num = int(message.content)
            if 1 <= answer_num <= len(question_data["options"]):
                user_answer = question_data["options"][answer_num - 1]
                is_correct = user_answer == question_data["correct_answer"]

                if is_correct:
                    points = 10
                    self.trivia_system.streak_counts[message.author.id] += 1
                    streak = self.trivia_system.streak_counts[message.author.id]
                    if streak > 1:
                        points += streak * 2  # Bonus points for streak

                    new_score = self.trivia_system.update_score(message.author.id, points)
                    response = f"Correct✅! You earned {points} points (Streak: {streak})\nTotal score: {new_score}"
                else:
                    self.trivia_system.streak_counts[message.author.id] = 0
                    response = f"Wrong❌! The correct answer was: {question_data['correct_answer']}"

                await message.channel.send(response)
                return is_correct

        except ValueError:
            await message.channel.send("Please enter a number between 1 and 4")
        return None

    async def on_ready(self):
        print(f"Logged in as {self.user}")
        print("APES is ready!")

    async def on_message(self, message):
        if message.author == self.user:
            return

        # Handle DMs
        if isinstance(message.channel, discord.DMChannel):
            await self.process_message(message, message.content)
            return

        # Handle server messages with commands
        if message.content.startswith('!'):
            command = message.content.lower().split()[0][1:]

            if command == 'trivia':
                question = self.trivia_system.get_random_question()
                embed = await self.create_trivia_embed(question)
                await message.channel.send(embed=embed)
                self.trivia_system.active_games[message.channel.id] = question



            elif command == 'leaderboard':
                leaderboard = self.trivia_system.get_leaderboard()
                embed = discord.Embed(title="🏆 Movie Trivia Leaderboard", color=discord.Color.gold())

                for i, (user_id, score) in enumerate(leaderboard[:10], 1):
                    user = await self.fetch_user(user_id)
                    embed.add_field(
                        name=f"{i}. {user.name}",
                        value=f"Score: {score}",
                        inline=False
                    )

                await message.channel.send(embed=embed)

            elif command == 'help':
                help_embed = discord.Embed(
                    title="🎬 Movie Bot Commands",
                    description="Here are the available commands:",
                    color=discord.Color.blue()
                )
                help_embed.add_field(name="!trivia", value="Start a movie trivia question", inline=False)
                help_embed.add_field(name="!flashcard", value="Get a random movie flashcard", inline=False)
                help_embed.add_field(name="!leaderboard", value="View the trivia leaderboard", inline=False)
                await message.channel.send(embed=help_embed)

        # Handle trivia answers
        elif message.channel.id in self.trivia_system.active_games:
            question = self.trivia_system.active_games[message.channel.id]
            result = await self.process_trivia_answer(message, question)
            if result is not None:
                del self.trivia_system.active_games[message.channel.id]

        # Handle regular chat with mentions
        elif self.user in message.mentions:
            user_message = message.content.replace(f"<@{self.user.id}>", "").strip()
            await self.process_message(message, user_message)



    async def process_message(self, message, user_message):
        response_message = await message.reply("Typing...")

        thread_id = await self.get_thread_option()
        prompts = self.opclient.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        run = self.opclient.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=self.assistant_id
        )

        while True:
            try:
                run = self.opclient.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                if run.completed_at:
                    messages = self.opclient.beta.threads.messages.list(thread_id=thread_id)
                    last_message = messages.data[0]
                    response = last_message.content[0].text.value
                    await response_message.edit(content=response)
                    break
            except Exception as e:
                logging.error(f"Error occurred while retrieving the data: {e}")
                break
            await asyncio.sleep(1)


# Initialize and run the bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.dm_messages = True
intents.reactions = True  # Enable reaction intents

bot = MovieBot(intents=intents)
bot.run(Discord_BOT_API_KEY)

