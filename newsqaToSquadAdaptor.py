# Converting from newsQA to SQuAD
import csv
import os as os
import pandas as pd
import re as regex
import json

filePathDataset = os.path.abspath("./data/newsQA/newsqa-data-v1.csv")
REPLACE_WITH_NO_SPACE = \
    regex.compile("(\()|(\,)|(\")|(\))|(\–)|(\;)|(\!)|(\-)|(<br />)|@highlight|(cnn)|(\:)|(\“)|(\’)|(\‘)|(\”)|(\')|(\\n)")
IS_TRAINING = True
TOTAL_IMPOSSIBLE_ANSWERS = 0
TOTAL_MULTIPLE_ANSWERS = 0
TOTAL_ONE_ANSWER = 0

# Function does first-level data cleaning
def getStoryPreProcessedContent(storyContent):
    content = regex.sub(REPLACE_WITH_NO_SPACE, "", storyContent).lower()
    return content

# Returns un-preprocessed escaped story
def getEscapedStory(story):
    return story.replace("\n", "\\n")

# Returns un-preprocessed story
def getStory(story):
    content = ""
    for line in story:
        content = content + line
    return content

# Function determines if at all an answer is present
def isAnswerPresent(answerArray):
    for i in range(0,len(answerArray)):
        if answerArray[i].lower().strip() != "none":
            return answerArray[i]

    return False

# TODO: 
def getAnswersAsText(answerArray, story, IS_TRAINING):
    answersList=[]
    for i in range(0,len(answerArray)):
        if answerArray[i].lower().strip() != "none":
            answerElement= {}
            rangeSplit = answerArray[i].split(":")
            # remove below filter once multi-range line answers are handled
            if rangeSplit[0].find(",") ==-1 and rangeSplit[1].find(",") ==-1:
                answer= story[int(rangeSplit[0]):int(rangeSplit[1])]
                answerElement["answer_start"] = int(rangeSplit[0])
                answerElement["text"] = answer.strip()
                answersList.append(answerElement)
    return answersList[0:1] if IS_TRAINING else answersList

# Function returns the answer of the question
def getAnswerGivenCharRange(ansCharRange,story):
    rangeSplit = ansCharRange.split(":")
    return story[int(rangeSplit[0]):int(rangeSplit[1])]

def getStartAnswerCharIndex(ansCharRange):
    rangeSplit = ansCharRange.split(":")
    return int(rangeSplit[0])

def createNewQuestion(question, answerArray, unprocessedStory, IS_TRAINING, q_id):
    # Building up of objects
    global TOTAL_IMPOSSIBLE_ANSWERS
    global TOTAL_MULTIPLE_ANSWERS
    global TOTAL_ONE_ANSWER
    qaElement= {}
    qaElement["answers"] = getAnswersAsText(answerArray, getEscapedStory(unprocessedStory), IS_TRAINING)
    qaElement["is_impossible"] = len(qaElement["answers"])==0
    if len(qaElement["answers"])==0:
        TOTAL_IMPOSSIBLE_ANSWERS +=1
    elif len(qaElement["answers"])>1:
        TOTAL_MULTIPLE_ANSWERS +=1 
    else:
        TOTAL_ONE_ANSWER += 1
    qaElement["question"] = question
    m = regex.search('./data/newsQA/cnn/stories/(.+?).story', id)
    unique_q_id = m.group(1) if m else id
    qaElement["id"] = unique_q_id+"_"+str(q_id)
    return qaElement

# Initializing
dataFrameDataSet = pd.read_csv(filePathDataset)
#dataFrameDataSet=dataFrameDataSet[:50]
dataFrameDataSet.dropna(how="all", inplace=True) 

squadWrapper = {}
data = dict()
data["data"] = []
storiesId = {}

# Construction of JSON data
#len(dataFrameDataSet)
for i in range(0, 1):
    # Skip if no answer present
    answerArray = (dataFrameDataSet["answer_char_ranges"][i]).split("|")
    answerPresence = isAnswerPresent(answerArray)

    if not answerPresence:
        # No answer present - don't add question/para to dataset
        continue

    id = dataFrameDataSet["story_id"][i]
    storiesPath = os.path.abspath("./data/" + id)
    if not os.path.isfile(storiesPath):
        raise TypeError(storiesPath + " is not present")

    story = open(storiesPath, encoding="utf-8")
    unprocessedStory = getStory(story)

    if id in storiesId:
        # paragraph already present, question has been added
        # print("Story already present")
        for storyElement in data["data"]:
            if storyElement["title"] == id:
                currentQuestions= storyElement["paragraphs"][0]["qas"]
                currentQuestions.append(
                    createNewQuestion(
                        dataFrameDataSet["question"][i], 
                        answerArray, 
                        unprocessedStory, IS_TRAINING, len(currentQuestions)+1))
                storyElement["paragraphs"][0]["qas"]= currentQuestions
    else:
        # new paragraph added
        storiesId[id] = True
        
        firstQuestion= []
        firstQuestion.append(createNewQuestion(dataFrameDataSet["question"][i], answerArray, unprocessedStory, IS_TRAINING, 1))
        
        # in news QA, we have 1 paragraph (but multiple queustions)
        # in SqUAD, we can have multiple paragraphs, so for consistency
        # we use a paragraphList with 1 entry here
        paragraphList= []
        paragraphElement = {}
        paragraphElement["context"] = unprocessedStory#getStoryPreProcessedContent(unprocessedStory)
        paragraphElement["qas"] = firstQuestion
        #paragraphElement["storyId"] = id
        paragraphList.append(paragraphElement)

        dataObject = {}
        dataObject["title"] = id
        dataObject["paragraphs"] = paragraphList
        data["data"].append(dataObject)

squadWrapper["data"] = data["data"]
squadWrapper["version"] = "1.1"

print("#############")
print("Total impossible answers: ",TOTAL_IMPOSSIBLE_ANSWERS)
print("Total multiple answers: ",TOTAL_MULTIPLE_ANSWERS)
print("Total single asnwers: ",TOTAL_ONE_ANSWER)
print("#############")

# Create new JSON File
with open('./data/newsQA/generated/complete/newsQaJSONSquadFormat_singleAnswers_delete.json', 'w') as f:
  json.dump(squadWrapper, f, ensure_ascii=False)

