import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont  # Import ImageFont
import io
import json
from dotenv import load_dotenv
import os

YOUR_API_KEY = os.environ.get('GEMINI_API_KEY')

def apply_image_modifications(img_path, modifications, output_folder="corrected_images"):
    """Applies image modifications to an image and saves it to the specified output folder.

    Args:
        img_path (str): Path to the image to modify.
        modifications (list): A list of modification instructions.
        output_folder (str): The folder to save the modified image.
    """
    try:
        img = Image.open(img_path)
        width, height = img.size  # Get image dimensions
        draw = ImageDraw.Draw(img)

        for mod in modifications:
            shape = mod['shape']
            color = mod['color']
            coords = mod['coordinates']
            text = mod['text']
            question_number = mod['question_number']
            line_width = mod.get('line_width', 2)  # Default line width
            font_size = mod.get('font_size', 16)  # Default font size

            font = ImageFont.truetype("arial.ttf", font_size)  # Or another font you have

            # Convert relative coordinates to absolute
            if shape in ["circle", "rectangle", "line"]:
                abs_coords = []
                for coord in coords:
                    if 0 <= coord <= 1: # If it's a ratio
                        abs_coords.append(coord * (width if coords.index(coord) % 2 == 0 else height)) #X are divided by width, y are divided by height
                    else:
                        abs_coords.append(coord) #Use the old data if not a ration
                coords = abs_coords

            if shape == "circle":
                # Assuming coords are [center_x, center_y, radius]
                x, y, r = coords
                draw.ellipse((x - r, y - r, x + r, y + r), outline=color, width=line_width)
            elif shape == "rectangle":
                # Assuming coords are [x1, y1, x2, y2]
                draw.rectangle(coords, outline=color, width=line_width)
            elif shape == "line":
                # Assuming coords are [x1, y1, x2, y2]
                draw.line(coords, fill=color, width=line_width)

            if text:
                # Adjust position for text as needed
                draw.text((coords[0], coords[1] + 10), text, fill=color, font=font)  # Use the font

        # Create the output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        # Save the modified image to the output folder
        base_filename = os.path.basename(img_path)  #Get the file name from the path
        filename, ext = os.path.splitext(base_filename) #Split the name and extension
        output_path = os.path.join(output_folder, f"{filename}_modified{ext}")
        img.save(output_path)
        print(f"Modified image saved as {output_path}")

    except FileNotFoundError:
        print(f"Error: Image file not found: {img_path}")
    except Exception as e:
        print(f"Error applying image modifications: {e}")


def grade_answer_gemini(problem_images, answer_images, grading_standards, scoring_difficulty, output_folder="corrected_images", model_name='gemini-1.5-flash'):
    """
    Grades student answers and generates image modification instructions.

    Args:
        problem_images (list of str or bytes): Paths to problem images.
        answer_images (list of str or bytes): Paths to answer images.
        grading_standards (str): Textual description of the grading standards.
        scoring_difficulty (int):  A value between 1-10 representing the stringency of grading. Higher values make it harder to get a high score.
        output_folder (str): The folder to save corrected images.
        model_name (str): The name of the Gemini model to use.

    Returns:
        dict: Grading results and image modification instructions.
    """

    genai.configure(api_key=YOUR_API_KEY)
    # Refresh the model instance with every call
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
        image_modifications = [] # A list to hold modification instructions for each image

        for i, answer_img in enumerate(answer_imgs):
            prompt = f"""
            You are an automated grader and image modification instructor. Analyze the student's answer sheet page and generate detailed instructions for correcting it.
            Problem Images: [PROBLEM_IMAGES]
            Student Answer Sheet Page {i+1}: [ANSWER_IMAGE]
            Grading Standards: [GRADING_STANDARDS]

            The scoring_difficulty for the question is {scoring_difficulty}!!!

            Review the provided images and identify each question *answered on this page*. Use the grading standards to score each question and suggest image annotations. A single page can contain multiple questions; identify and grade all of them. If a question is unanswered, score it as zero.

            For each question identified on this page:
            - Provide a score (0-10) based on the grading standards, taking into account the scoring difficulty. 
            The scoring_difficulty for the question is {scoring_difficulty}!!!
            Scoring difficulty means:

            *   **If the scoring difficulty is 10:** The grading is extremely strict. To achieve a high score, the student MUST meticulously cover *every* key point and detail listed in the grading standards. The answer should be worded in precise terminology and cover with depth. Even using synonyms or omitting minor details will result in deductions.
                *Example: For Question Reasons for the rise of the Roman Empire, a score of 10 would require discussing Military strength, geography, infrastructure, political structure, economic power, cultural assimilation, and strong leadership comprehensively with specifics for each. Omitting even one would lower the score.*

            *   **If the scoring difficulty is 5:** The grading is not hard. To achieve full score, the student needs to demonstrate a general understanding of the topic. The answer needs to be reasonably related to the key points, it does not need to be in the grading standers but highly resonable, single mistakes or missing can be ignored. It's easy to get high score even the answer is partial correct.
                *Example: For Question Reasons for the rise of the Roman Empire, a high score could be given even if the answer only discusses "military strength" and "geography". similar things like technology and culture can also get some score as long as it's not logically wrong, but need more explanation to get full *

            *   **If the scoring difficulty is 1:** The grading is very lenient. To achieve full score, the student needs only to demonstrate a general understanding of the topic, as long as they don't provide fake truth or logical fallacies. The answer needs to be only reasonably related to the topic, it does not need to be in the grading standers, some mistakes or missing can be ignored. It's easy to get full score even the answer is correct but totally different from the stander one.
                *Example: For Question Reasons for the rise of the Roman Empire, a high score could be given even if the answer only discusses "military strength" and "geography". similar things like technology and culture can also get full score as long as it's not logically wrong*

            *   **If the scoring difficulty is between 2 and 9:** The grading falls on a spectrum between these two extremes. Higher numbers mean stricter grading, and lower numbers mean more lenient grading. Use your best judgement to assign the score.

            - Provide a *concise* overall analysis explaining the score in relation to the grading criteria, considering the scoring difficulty. End your analysis with this sentence exactly: "Considering that the current difficulty is {scoring_difficulty}, the score should be..." Do not break down the score into separate score points. Focus on the answer's overall strengths and weaknesses.

            The scoring_difficulty for the question is {scoring_difficulty}!!!

            In addition to grading, suggest concise and clear instructions for marking incorrect or incomplete areas on the image (shape, color, coordinates, text). Keep the text for image modifications short and specific. Please output the x,y coordinates in range [0,1], make it a relative position in the picture.

            Respond in JSON format with a list of question results and image modification instructions. If you can't create valid JSON, respond with just 0.
            
            ```json
            {{
                "page_results": [
                    {{
                        "question_number": <integer>,
                        "score": <integer>,
                        "analysis": "<overall analysis of the answer> Considering that the current difficulty is {scoring_difficulty}, the score should be...",
                    }},
                    ...
                ],
                "image_modifications": [
                    {{
                        "shape": "<shape to draw (e.g., circle, rectangle, line)>",
                        "color": "<color of the shape (e.g., red, blue)>",
                        "coordinates": [<x1>, <y1>, <x2>, <y2>]  // or [<center_x>, <center_y>, <radius>] for circles, in ratio range [0,1]
                        "line_width": <integer>,
                        "font_size": <integer>,
                        "text": "<short, clear correction text>",
                        "question_number": <question number the modification refers to>
                    }},
                    ...
                ]
            }}
            ```

            If no questions are answered on this page, respond with 0.
            """

            PROBLEM_IMAGES_DISPLAY = f"Multiple Problem Images (specify topics in grading standards for best performance)."
            ANSWER_IMAGE_DISPLAY = f"Student Answer Sheet Page {i+1} Image Data: Student's answers to questions from the problem set (this is page {i+1})."
            prompt = prompt.replace("[PROBLEM_IMAGES]", PROBLEM_IMAGES_DISPLAY)
            prompt = prompt.replace("[ANSWER_IMAGE]", ANSWER_IMAGE_DISPLAY)
            prompt = prompt.replace("[GRADING_STANDARDS]", grading_standards)

            images_for_prompt = problem_imgs + [answer_img]
            response = model.generate_content(images_for_prompt + [prompt])

            if response.prompt_feedback:
                print(f"Prompt Feedback (Answer Sheet Page {i+1}):", response.prompt_feedback)

            response.resolve()

            try:
                try:
                    json_string = response.text.strip()
                    if json_string.startswith("```json"):
                        json_string = json_string[len("```json"):].strip()
                    if json_string.endswith("```"):
                        json_string = json_string[:-len("```")].strip()

                    if json_string == "0":
                        print(f"Answer Sheet Page {i+1}: No answers found on this page.")
                        image_modifications.append([]) # Append an empty list to indicate no modifications
                        continue

                    result = json.loads(json_string)
                    page_results = result.get("page_results")
                    modifications = result.get("image_modifications")  # Get the image modification instructions
                    image_modifications.append(modifications if modifications else [])  # Add modifications, or an empty list if none.


                    if page_results is None:
                        raise ValueError(f"The response for Answer Sheet Page {i+1} did not contain 'page_results'. Invalid format.")

                    for question_result in page_results:
                         if not isinstance(question_result, dict):
                            print(f"Warning: Expected a dictionary for question_result, got {type(question_result)}. Skipping this result.")
                            continue
                         score = question_result.get("score")
                         analysis = question_result.get("analysis")

                         if score is None or analysis is None:
                            print(f"Warning: Missing 'score' or 'analysis' for a question. Skipping this question.")
                            continue

                         all_scores.append(score)
                         all_analyses.append(analysis)


                except json.JSONDecodeError as e:
                    print(f"JSONDecodeError for Answer Sheet Page {i+1}: {e}")
                    print(f"Raw response text for Answer Sheet Page {i+1}: {response.text}")
                    image_modifications.append([]) # Append empty modification instruction list
                    if response.text.strip() == "0":
                        all_scores.append(0)
                        all_analyses.append({"error": f"Gemini API returned 0 for Answer Sheet Page {i+1} due to safety restrictions/errors or because no answers were provided."})
                    else:
                        all_scores.append(0)
                        all_analyses.append({"error": f"Failed to decode JSON for Answer Sheet Page {i+1}. Raw response needs investigation."})
                except ValueError as e:
                    print(f"ValueError for Answer Sheet Page {i+1}: {e}")
                    image_modifications.append([]) # Append empty modification instruction list
                    all_scores.append(0)
                    all_analyses.append({"error": str(e)})

            except Exception as e:
                print(f"Unexpected error occurred for Answer Sheet Page {i+1}: {e}")
                image_modifications.append([]) # Append empty modification instruction list
                all_scores.append(0)
                all_analyses.append({"error": f"An unexpected error occurred on Answer Sheet Page {i+1}: {e}"})

        # Calculate final score (example - can be adjusted based on grading standards)
        final_score = sum(all_scores)

        # Generate overall feedback
        feedback_prompt = f"""
        You have graded a student's multi-page test paper. The final score is {final_score}.
        Provide general feedback on student performance, highlighting strengths and weaknesses based on the individual question analyses from all pages.
        Analyses: {all_analyses}
        Grading Standards: {grading_standards}

        Keep the response concise and helpful. Mention the strongest and weakest areas based on the score ranges.
        """
        feedback_response = model.generate_content(feedback_prompt)
        feedback_response.resolve()
        overall_feedback = feedback_response.text

        return {
            "scores": all_scores,
            "analyses": all_analyses,
            "final_score": final_score,
            "feedback": overall_feedback,
            "image_modifications": image_modifications  # Return the modification instructions
        }
    except FileNotFoundError as e:
        print(e)
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Load environment variables from .env file
# load_dotenv()

# if __name__ == '__main__':
#     # Check API key
#     try:
#         if not YOUR_API_KEY:
#             while True:
#                 api_key = input("Please enter your Gemini API key: ")
#                 if api_key:
#                     os.environ['GEMINI_API_KEY'] = api_key
#                     YOUR_API_KEY = api_key
#                     break
#                 else:
#                     print("API key cannot be empty. Please try again.")
#     except Exception as e:
#         print(f"An error occurred when setting API Key: {e}")
#         exit()
#     # Example Usage
#     PROBLEM_IMAGES = ["imgs/testPaperA.png"]
#     ANSWER_IMAGES = ["imgs/testPaperA.png"]  # Using testPaper again for demo
#     GRADING_STANDARDS = """
# Question 3: Probability of More Than 2 Cookies (10 points)

# Concept Understanding (3 points):

# 3 points: Correctly identifies the need to use the complement rule (P(X > 2) = 1 - P(X <= 2)). The use of complement rule must be stated.

# 0 points: Fails to recognize the correct approach to solve this problem

# Probability Identification (3 points):

# 2 points: Correctly identifies the values of P(0), P(1), and P(2) from the initial information or uses provided values correctly. Must write P(0), P(1) and P(2).

# 0 points: Incorrect or missing identification of values.

# Calculation (4 points):

# 4 points: Calculates P(X <= 2) = P(0) + P(1) + P(2), then calculates P(X > 2) correctly. If any calculation is wrong, deduct 2 points, must use the correct format.

# 0 points: Incorrect calculation or missing final answer.

# Expected Answer Format:

# P(X > 2) = 1 - [P(0) + P(1) + P(2)]
#         = 1 - [0.7 + 0.21 + 0.063]
#         = 1 - 0.973
#         = 0.027
# Use code with caution.
# Question 4: Geometric Random Variable - Mean, Variance, and Standard Deviation (10 points)

# Correct Formulas (3 points):

# 3 points: States the correct formulas for the mean (E[X] = (1-p)/p), variance (V[X] = (1-p)/p^2), and standard deviation (σ = sqrt(V[X])) of a geometric random variable. Must be correct formula with right expression.

# 0 points: Incorrect or missing formulas.

# Correct Substitution (3 points):

# 3 points: Correctly identifies and substitutes the value of 'p' (probability of success) from the context into the formulas.
# Assume p=0.7

# 0 points: Incorrect or missing substitution.

# Accurate Calculations (4 points):

# 4 points: Correctly calculates the mean, variance, and standard deviation based on the formulas and 'p' value. If one expression are wrong, 2 point deduction.

# 0 points: Incorrect calculation or missing final answer.

# Expected Answer Format (Using p = 0.7):

# E[X] = (1-0.7)/0.7 = 0.3/0.7 = 3/7 ≈ 0.428
# V[X] = (1-0.7)/(0.7)^2 = 0.3 / 0.49 ≈ 0.612
# σ = sqrt(V[X]) = sqrt(0.612) ≈ 0.782
# Use code with caution.
# General Notes for Both Questions:

# Partial Credit: Partial credit may be awarded for showing the correct steps, even if the final answer is incorrect due to a minor arithmetic error.

# Units: The inclusion or omission of units (e.g., "cookies") will not be penalized.

# Rounding: Minor differences in rounding will generally not be penalized, as long as the student's work is consistent.

# Presentation: While neatness is appreciated, the focus is on the correctness of the solution.Illegible work will be assessed at zero.    """

#     grading_results = grade_answer_gemini(PROBLEM_IMAGES, ANSWER_IMAGES, GRADING_STANDARDS, scoring_difficulty=5)

#     if grading_results:
#         print("Grading Results:")
#         print(f"Final Score: {grading_results['final_score']}")
#         print("Individual Scores:", grading_results['scores'])
#         print("Analyses:", grading_results['analyses'])
#         print("Overall Feedback:", grading_results['feedback'])
#         print("Image Modification Instructions:", grading_results['image_modifications'])

#         # Example of how you might apply the modifications (This part requires PIL and is just an example)
#         try:

#             for i, modifications in enumerate(grading_results['image_modifications']):
#                 img_path = ANSWER_IMAGES[i]  # Get the path to the corresponding answer image
#                 apply_image_modifications(img_path, modifications)

#         except ImportError:
#             print("PIL is not installed. Install it to apply the image modifications.")
#         except Exception as e:
#             print(f"Error applying image modifications: {e}")