import google.generativeai as genai
from PIL import Image
import io
import json
from dotenv import load_dotenv
import os


YOUR_API_KEY = os.environ.get('GEMINI_API_KEY')

def grade_answer_gemini(problem_images, answer_images, grading_standards, model_name='gemini-1.5-flash'):
    """
    Grades student answers based on multiple problem images and answer images, using Gemini.

    Args:
        problem_images (list of str or bytes): List of paths to problem images or image data (bytes).
        answer_images (list of str or bytes): List of paths to answer images or image data (bytes).
        grading_standards (str): Textual description of the grading standards (score points, rubric).
        model_name (str): The name of the Gemini model to use.

    Returns:
        dict: A dictionary containing the grading results, including:
            - "scores": A list of scores for each answer image.
            - "analyses": A list of analyses for each answer image, broken down by score point.
            - "final_score": The final score, calculated based on the grading standards.
            - "feedback": Overall feedback on the answers.
    """

    genai.configure(api_key=YOUR_API_KEY)
    model = genai.GenerativeModel(model_name)

    def load_image(image_data):
        """Helper function to load image data, handling both file paths and bytes."""
        try:
            if isinstance(image_data, str): # assume it's a path
                return Image.open(image_data)
            elif isinstance(image_data, bytes): # it's already the image data
                return Image.open(io.BytesIO(image_data)) # use io.BytesIO to convert bytes to file-like object
            else:
                raise TypeError("Image data must be a file path (string) or image data (bytes).")
        except FileNotFoundError:
            raise FileNotFoundError(f"Image file not found: {image_data}")
        except Exception as e:
            raise Exception(f"Error loading image: {e}")

    try:
        problem_imgs = [load_image(img) for img in problem_images]
        answer_imgs = [load_image(img) for img in answer_images]

        all_scores = []
        all_analyses = []

        for i, answer_img in enumerate(answer_imgs):
            prompt = f"""
            You are an automated grader. Analyze the student's answer sheet page.
            Problem Images: [PROBLEM_IMAGES]
            Student Answer Sheet Page {i+1}: [ANSWER_IMAGE]
            Grading Standards: [GRADING_STANDARDS]

            Review the multiple problem images provided, and then assess the *current answer sheet page*.
            Identify each question *answered on this page* and provide a score (integer) for each question based on the grading standards.  Score should be between 0-10 for each question. If no questions are answered on this page, simply return 0.
            Provide a detailed analysis breaking down the score by each score point mentioned in the grading standards for *each* question on this page.
            Explain why the student received the score they did for each question on this page.

            Respond in JSON format with a single JSON object containing a list of question results for *this page*. If you cannot create a valid JSON object due to safety restrictions or other errors, respond with just the integer 0.

            ```json
            {{
                "page_results": [
                    {{
                        "question_number": <integer>,
                        "score": <integer>,
                        "analysis": {{
                            "score_point_1": "<analysis and score for score point 1>",
                            "score_point_2": "<analysis and score for score point 2>",
                            ...
                        }}
                    }},
                    {{
                        "question_number": <integer>,
                        "score": <integer>,
                        "analysis": {{
                            "score_point_1": "<analysis and score for score point 1>",
                            "score_point_2": "<analysis and score for score point 2>",
                            ...
                        }}
                    }},
                    ...
                ]
            }}
            ```
            If this page contains no answers, respond with 0.
            """

            PROBLEM_IMAGES_DISPLAY = f"Multiple Problem Images (specify topics in grading standards for best performance)."  # More general description
            ANSWER_IMAGE_DISPLAY = f"Student Answer Sheet Page {i+1} Image Data: Student's answers to questions from the problem set (this is page {i+1})." # description of image so the prompt makes sense
            prompt = prompt.replace("[PROBLEM_IMAGES]", PROBLEM_IMAGES_DISPLAY)
            prompt = prompt.replace("[ANSWER_IMAGE]", ANSWER_IMAGE_DISPLAY)
            prompt = prompt.replace("[GRADING_STANDARDS]", grading_standards)

            # Pass all problem images along with the answer image.
            images_for_prompt = problem_imgs + [answer_img]
            response = model.generate_content(images_for_prompt + [prompt])

            if response.prompt_feedback:
                print(f"Prompt Feedback (Answer Sheet Page {i+1}):", response.prompt_feedback)

            response.resolve()

            try:
                try:
                    # Strip the ```json and ``` from the response
                    json_string = response.text.strip()
                    if json_string.startswith("```json"):
                        json_string = json_string[len("```json"):].strip()
                    if json_string.endswith("```"):
                        json_string = json_string[:-len("```")].strip()

                    # Before parsing as JSON, check if response is just "0":
                    if json_string == "0":
                      print(f"Answer Sheet Page {i+1}: No answers found on this page.")
                      continue  # Skip processing this page, no actual results.

                    result = json.loads(json_string)
                    page_results = result.get("page_results") # Get the list of question results

                    if page_results is None:
                        raise ValueError(f"The response for Answer Sheet Page {i+1} did not contain 'page_results'. Invalid format.")

                    for question_result in page_results:
                        score = question_result.get("score")
                        analysis = question_result.get("analysis")

                        if score is None or analysis is None:
                            print(f"Missing 'score' or 'analysis' for a question on Answer Sheet Page {i+1}.")
                            continue # Skip to the next question if something is missing

                        all_scores.append(score)  # Add to overall scores
                        all_analyses.append(analysis)

                except json.JSONDecodeError as e:
                    print(f"JSONDecodeError for Answer Sheet Page {i+1}: {e}")
                    print(f"Raw response text for Answer Sheet Page {i+1}: {response.text}")
                    if response.text.strip() == "0":
                        all_scores.append(0)
                        all_analyses.append({"error": f"Gemini API returned 0 for Answer Sheet Page {i+1} due to safety restrictions/errors or because no answers were provided."})
                    else:
                        all_scores.append(0)
                        all_analyses.append({"error": f"Failed to decode JSON for Answer Sheet Page {i+1}. Raw response needs investigation."})
                except ValueError as e:
                    print(f"ValueError for Answer Sheet Page {i+1}: {e}")
                    all_scores.append(0)
                    all_analyses.append({"error": str(e)})

            except Exception as e:
                print(f"Unexpected error occurred for Answer Sheet Page {i+1}: {e}")
                all_scores.append(0)
                all_analyses.append({"error": f"An unexpected error occurred on Answer Sheet Page {i+1}: {e}"})

        # Calculate final score (example - can be adjusted based on grading standards)
        final_score = sum(all_scores)  # Total Score instead of Average - Makes More Sense in this context.

        # Generate overall feedback
        feedback_prompt = f"""
        You have graded a student's multi-page test paper. The final score is {final_score}.
        Provide general feedback on student performance, highlighting strengths and weaknesses based on the individual question analyses from all pages.
        Analyses: {all_analyses}
        Grading Standards: {grading_standards}

        Keep the response concise and helpful.  Mention the strongest and weakest areas based on the score ranges.
        """
        feedback_response = model.generate_content(feedback_prompt)
        feedback_response.resolve()
        overall_feedback = feedback_response.text

        return {
            "scores": all_scores,
            "analyses": all_analyses,
            "final_score": final_score,
            "feedback": overall_feedback
        }

    except FileNotFoundError as e:
        print(e)
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# # Load environment variables from .env file
# load_dotenv()


# if __name__ == '__main__':
#     # Example usage
#     PROBLEM_IMAGES = ["imgs\\testPaper.png"]  # Replace with actual paths to the problem images
#     ANSWER_IMAGES = ["imgs\\ans1.png", "imgs\\ans2.png", "imgs\\ans3.png"]  # Replace with paths to the student's answer sheet pages.
#     GRADING_STANDARDS = """
# General Instructions: Grade each question independently based on the concepts and keywords listed below.

# Test Paper 1: History of the Roman Empire

# Question 1 (May be found on any page): What were the main reasons for the rise of the Roman Empire? (Max Score: 10)
#     Keywords: Republic, Military, Expansion, Trade, Politics
#     Concepts: Describe how Rome grew from a small city-state to a dominant power in the Mediterranean.

# Question 2 (May be found on any page): Explain the role of Julius Caesar in the late Roman Republic. (Max Score: 10)
#     Keywords: Dictator, Reform, Power, Civil War, Senate
#     Concepts: Discuss Caesar's impact on the transition from Republic to Empire.

# Test Paper 2: Calculus

# Question 3 (May be found on any page): Solve for x: 2x + 5 = 11 (Max Score: 10)
#     Keywords: Algebra, Equation, Solve
#     Concepts: Correctly isolate x to find the solution.

# Question 4 (May be found on any page): Differentiate f(x) = x^3 + 2x^2 - x + 5 (Max Score: 10)
#     Keywords: Derivative, Power Rule, Differentiation
#     Concepts: Apply the power rule correctly to find the derivative.
#     """

#     grading_results = grade_answer_gemini(PROBLEM_IMAGES, ANSWER_IMAGES, GRADING_STANDARDS)

#     if grading_results:
#         print("Grading Results:")
#         print(f"Final Score: {grading_results['final_score']}")
#         print("Individual Scores:", grading_results['scores'])
#         print("Analyses:", grading_results['analyses'])
#         print("Overall Feedback:", grading_results['feedback'])
#     else:
#         print("Failed to grade answers.")