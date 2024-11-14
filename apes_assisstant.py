import openai
from openai import OpenAI
#Creation of OPENAI assisstant which will be used only once
client = OpenAI()
assisstant = client.beta.assistants.create(
            name="APES",
            instructions=""" You are a movie recommender system named APES, who's gonna ask few questions like trivia 
            to understand what the user wants like start with 3-4 questions, which can include genre, mood, 


        """,
        model='gpt-3.5-turbo'
        )

ASSISSTANT_ID = assisstant.id




