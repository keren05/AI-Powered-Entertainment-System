import discord
from openai import OpenAI
import asyncio
import time
import logging
import random
import json
from datetime import datetime, timedelta
from collections import defaultdict
import aiohttp


opclient = OpenAI(
)
from apes_assisstant import ASSISSTANT_ID
Discord_BOT_API_KEY="YOUR DISCORD KEY"

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)
class MovieStreamingService:
    def __init__(self):
        # Dictionary to store streaming service information for movies
        self.streaming_services = {
            "Netflix": "https://www.netflix.com/search?q=",
            "Amazon Prime": "https://www.amazon.com/s?k=",
            "Disney+": "https://www.disneyplus.com/search?q=",
            "Hulu": "https://www.hulu.com/search?q=",
            "HBO Max": "https://www.max.com/search?q="
        }

    async def get_watch_options(self, movie_title):
        """
        Get streaming service availability for a movie.
        In a production environment, you would want to replace this with a real API call
        to a service like JustWatch API or TMDB API.
        """
        try:
            # Example API endpoint - replace with actual streaming data API
            async with aiohttp.ClientSession() as session:
                # Replace this URL with actual API endpoint
                api_url = f"https://api.watchmode.com/v1/title/{movie_title}/sources"
                # Add your API key and other necessary parameters
                params = {
                    "apiKey": "YOUR_API_KEY"
                }

                async with session.get(api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._format_watch_options(data)
                    else:
                        return "Streaming information unavailable"

        except Exception as e:
            logging.error(f"Error fetching streaming data: {e}")
            return "Unable to fetch streaming information at this time."

    def _format_watch_options(self, data):
        """Format the streaming options into a readable message"""
        # This is a placeholder implementation - modify based on actual API response
        services = []
        for service, base_url in self.streaming_services.items():
            if random.choice([True, False]):  # Simulate random availability
                services.append(f"[{service}]({base_url})")

        if services:
            return f"Available on: {', '.join(services)}"
        return "Not currently available on major streaming services"


class MovieTriviaSystem:
    def __init__(self):
        self.streaming_service = MovieStreamingService()

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
            }
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

    async def get_movie_info(self, movie_title):
        """Get movie information including streaming options"""
        streaming_info = await self.streaming_service.get_watch_options(movie_title)
        return streaming_info


class MovieBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trivia_system = MovieTriviaSystem()
        self.opclient = OpenAI()
        self.assistant_id = ASSISSTANT_ID
        self.thread_id = None

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

        # Add streaming information for the correct answer
        streaming_info = await self.trivia_system.get_movie_info(question_data["correct_answer"])
        embed.add_field(
            name="Where to Watch",
            value="Answer the question to see where you can watch this movie!",
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
                        points += streak * 2

                    new_score = self.trivia_system.update_score(message.author.id, points)

                    # Get streaming information
                    streaming_info = await self.trivia_system.get_movie_info(question_data["correct_answer"])

                    embed = discord.Embed(
                        title="Correct Answer!",
                        description=f"You earned {points} points (Streak: {streak})\nTotal score: {new_score}",
                        color=discord.Color.green()
                    )

                    embed.add_field(
                        name=f"Watch {question_data['correct_answer']}",
                        value=streaming_info,
                        inline=False
                    )

                    await message.channel.send(embed=embed)
                else:
                    self.trivia_system.streak_counts[message.author.id] = 0
                    embed = discord.Embed(
                        title="Wrong Answer!",
                        description=f"The correct answer was: {question_data['correct_answer']}",
                        color=discord.Color.red()
                    )

                    # Get streaming information
                    streaming_info = await self.trivia_system.get_movie_info(question_data["correct_answer"])
                    embed.add_field(
                        name="Where to Watch",
                        value=streaming_info,
                        inline=False
                    )

                    await message.channel.send(embed=embed)
                return is_correct

        except ValueError:
            await message.channel.send("Please enter a number between 1 and 4")
        return None

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

                    # Check if the response contains a movie recommendation
                    # This assumes the assistant's response format includes movie titles in quotes
                    import re
                    movie_titles = re.findall(r'"([^"]*)"', response)

                    if movie_titles:
                        embed = discord.Embed(
                            title="Movie Recommendation",
                            description=response,
                            color=discord.Color.blue()
                        )

                        # Add streaming information for each mentioned movie
                        for movie in movie_titles:
                            streaming_info = await self.trivia_system.get_movie_info(movie)
                            embed.add_field(
                                name=f"Where to Watch '{movie}'",
                                value=streaming_info,
                                inline=False
                            )

                        await response_message.edit(embed=embed)
                    else:
                        await response_message.edit(content=response)
                    break
            except Exception as e:
                logging.error(f"Error occurred while retrieving the data: {e}")
                break
            await asyncio.sleep(1)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.dm_messages = True
intents.reactions = True  # Enable reaction intents

bot = MovieBot(intents=intents)
bot.run(Discord_BOT_API_KEY)