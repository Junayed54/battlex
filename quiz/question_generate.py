import pandas as pd
import random

leng = 0
# Generate unique question data
def generate_unique_questions(num_questions):
    subjects = ["Math", "Science", "History", "Geography", "Literature"]
    sections = ["Algebra", "Biology", "World History", "Physical Geography", "Shakespeare"]
    categories = ["Basic", "Intermediate", "Advanced"]
    difficulties = [1, 2, 3, 4, 5, 6]  # Difficulty levels

    # Sample base questions
    base_questions = [
        "What is 2 + 2?", "What is the capital of France?", 
        "Who wrote 'Hamlet'?", "What is the process of photosynthesis?", 
        "What is the largest planet in our solar system?", "What is the boiling point of water?",
        "Who discovered penicillin?", "What is the Pythagorean theorem?", 
        "What is the chemical formula for water?", "What is the main language spoken in Brazil?", 
        "What year did World War II end?", "What is the smallest prime number?",
        "What is the square root of 16?", "Who painted the Mona Lisa?", 
        "What is the capital of Japan?", "What is Newton's second law of motion?", 
        "What is the theory of relativity?", "What are the three states of matter?", 
        "Who was the first president of the United States?", "What is the currency of the United Kingdom?",
        "What is the formula for calculating area of a circle?", "What is the main ingredient in guacamole?",
        "What planet is known as the Red Planet?", "What gas do plants absorb from the atmosphere?",
        "What is the hardest natural substance on Earth?", "What is the longest river in the world?",
        "What is the capital of Canada?", "What is the process of cellular respiration?", 
        "What element has the chemical symbol 'O'?", "Who is known as the father of geometry?", 
        "What is the main theme of 'Pride and Prejudice'?"
    ]

    leng = len(base_questions)
    questions = []
    for i in range(num_questions):
        question_text = random.choice(base_questions)
        base_questions.remove(question_text)  # Remove to avoid duplicates

        option1 = "Option A"
        option2 = "Option B"
        option3 = "Option C"
        option4 = "Option D"
        answer = option1  # Assuming option1 is always the correct answer for simplicity

        subject = random.choice(subjects)
        section = random.choice(sections)
        category = random.choice(categories)
        difficulty = random.choice(difficulties)

        questions.append({
            "Question": question_text,
            "Option1": option1,
            "Option2": option2,
            "Option3": option3,
            "Option4": option4,
            "Answer": answer,
            "Options_num": 4,
            "Subject": subject,
            "Section": section,
            "Category": category,
            "Difficulty": difficulty
        })

    return pd.DataFrame(questions)

# Generate a DataFrame with 50 unique questions
questions_df = generate_unique_questions(leng)

# Save the DataFrame to an Excel file
file_path = 'supload_questions.xlsx'
questions_df.to_excel(file_path, index=False)

file_path
