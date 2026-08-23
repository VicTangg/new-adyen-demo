(() => {
  const prompts = [
    {
      prompt: "How do I find courage?",
      reply: "Courage is not waiting for the fear to disappear. It is taking one small step while the fear is still there.",
    },
    {
      prompt: "What keeps a team strong?",
      reply: "Trust. Listen closely, show up for each other, and celebrate every voice in the room.",
    },
    {
      prompt: "How do I prepare for a big moment?",
      reply: "Practice the details, breathe before the lights come up, and remember why you started.",
    },
    {
      prompt: "Can I get some encouragement?",
      reply: "You have already made it through every hard day behind you. Keep your focus forward, star.",
    },
  ];

  const question = (prompt, answer, explanation) => ({ prompt, answer, explanation });
  const mathQuestions = [
    question("What is 27 + 35?", 62, "Break 35 into 30 and 5: 27 + 30 + 5 = 62."),
    question("What is 46 + 28?", 74, "Add 20, then 8: 46 + 20 + 8 = 74."),
    question("What is 125 + 34?", 159, "125 + 30 = 155, then add 4."),
    question("What is 218 + 151?", 369, "Add hundreds, tens, and ones: 200 + 100, 10 + 50, and 8 + 1."),
    question("What is 307 + 46?", 353, "307 + 40 = 347, then add 6."),
    question("What is 89 + 67?", 156, "89 + 60 = 149, then add 7."),
    question("What is 144 + 228?", 372, "144 + 200 = 344, then add 28."),
    question("What is 560 + 120?", 680, "Add the hundreds and tens: 560 + 120 = 680."),
    question("What is 399 + 201?", 600, "399 needs 1 more to make 400, then add the remaining 200."),
    question("What is 75 + 125?", 200, "75 and 125 make two hundreds together."),

    question("What is 84 − 29?", 55, "Subtract 30 to get 54, then add 1 back."),
    question("What is 143 − 58?", 85, "143 − 50 = 93, then subtract 8."),
    question("What is 300 − 127?", 173, "300 − 100 = 200, then subtract 27."),
    question("What is 502 − 240?", 262, "Subtract 200, then subtract 40."),
    question("What is 1,000 − 475?", 525, "1,000 − 400 = 600, then subtract 75."),
    question("What is 90 − 36?", 54, "90 − 30 = 60, then subtract 6."),
    question("What is 261 − 119?", 142, "261 − 100 = 161, then subtract 19."),
    question("What is 700 − 385?", 315, "700 − 300 = 400, then subtract 85."),
    question("What is 450 − 99?", 351, "Subtract 100 to get 350, then add 1 back."),
    question("What is 600 − 278?", 322, "600 − 200 = 400, then subtract 78."),

    question("What is 3 × 4?", 12, "Three groups of four make twelve."),
    question("What is 5 × 6?", 30, "Five groups of six make thirty."),
    question("What is 7 × 4?", 28, "Seven groups of four make twenty-eight."),
    question("What is 8 × 3?", 24, "Eight groups of three make twenty-four."),
    question("What is 9 × 5?", 45, "Nine groups of five make forty-five."),
    question("What is 6 × 6?", 36, "Six groups of six make thirty-six."),
    question("What is 10 × 7?", 70, "Ten groups of seven make seventy."),
    question("What is 2 × 9?", 18, "Two groups of nine make eighteen."),
    question("What is 4 × 8?", 32, "Four groups of eight make thirty-two."),
    question("What is 3 × 9?", 27, "Three groups of nine make twenty-seven."),

    question("24 shared equally among 3 people gives how many each?", 8, "24 ÷ 3 = 8."),
    question("35 shared equally among 5 people gives how many each?", 7, "35 ÷ 5 = 7."),
    question("42 shared equally among 6 people gives how many each?", 7, "42 ÷ 6 = 7."),
    question("32 shared equally among 4 people gives how many each?", 8, "32 ÷ 4 = 8."),
    question("45 shared equally among 9 people gives how many each?", 5, "45 ÷ 9 = 5."),
    question("56 shared equally among 7 people gives how many each?", 8, "56 ÷ 7 = 8."),
    question("18 shared equally among 2 people gives how many each?", 9, "18 ÷ 2 = 9."),
    question("63 shared equally among 7 people gives how many each?", 9, "63 ÷ 7 = 9."),
    question("54 shared equally among 6 people gives how many each?", 9, "54 ÷ 6 = 9."),
    question("40 shared equally among 5 people gives how many each?", 8, "40 ÷ 5 = 8."),

    question("What is the value of the 7 in 472?", 70, "The 7 is in the tens place, so it means 70."),
    question("What number has 3 hundreds, 4 tens, and 6 ones?", 346, "300 + 40 + 6 = 346."),
    question("Which number is greatest: 509, 590, or 950?", 950, "950 has 9 hundreds, more than the other choices."),
    question("Which number is smallest: 718, 781, or 187?", 187, "187 has 1 hundred, fewer than 7 hundreds."),
    question("What number is 600 + 30 + 9?", 639, "Combine the hundreds, tens, and ones."),
    question("Round 825 to the nearest ten.", 830, "The ones digit is 5, so round the tens up."),
    question("Round 372 to the nearest hundred.", 400, "372 is closer to 400 than to 300."),
    question("What comes next: 145, 155, 165, ___?", 175, "The pattern adds 10 each time."),
    question("What number has 5 hundreds, 2 tens, and 4 ones?", 524, "500 + 20 + 4 = 524."),
    question("Which is greater: 608 or 680?", 680, "Both have 6 hundreds, but 8 tens is greater than 0 tens."),

    question("What is half of 12?", 6, "Split 12 into two equal groups: 6 in each."),
    question("What is one quarter of 20?", 5, "20 split into 4 equal groups gives 5."),
    question("How many equal parts are in fourths?", 4, "The word fourths means 4 equal parts."),
    question("What is three quarters of 8?", 6, "One quarter of 8 is 2, and three quarters is 2 + 2 + 2."),
    question("What is half of 18?", 9, "18 split into 2 equal groups gives 9."),
    question("What is one third of 15?", 5, "15 split into 3 equal groups gives 5."),
    question("How many equal parts are in fifths?", 5, "The word fifths means 5 equal parts."),
    question("What is half of 30?", 15, "30 split into 2 equal groups gives 15."),
    question("A pizza has 8 equal slices. You eat 3. How many slices remain?", 5, "8 − 3 = 5 slices remain."),
    question("How many more is one half of 12 than one quarter of 12?", 3, "Half of 12 is 6 and one quarter of 12 is 3."),
    question("There are 12 apples. One third are green. How many are green?", 4, "12 split into 3 equal groups gives 4."),
    question("A ribbon is cut into halves. How many equal pieces are there?", 2, "Halves means 2 equal pieces."),
    question("What is three quarters of 12?", 9, "One quarter is 3, so three quarters is 3 + 3 + 3."),
    question("What is one quarter of 16?", 4, "16 split into 4 equal groups gives 4."),
    question("A cake is shared in sixths. How many equal pieces are there?", 6, "Sixths means 6 equal pieces."),

    question("How many centimetres are in 1 metre?", 100, "1 metre equals 100 centimetres."),
    question("How many centimetres are in 3 metres?", 300, "3 × 100 = 300 centimetres."),
    question("A ribbon is 250 cm long. After using 2 m, how many centimetres remain?", 50, "2 m is 200 cm, and 250 − 200 = 50."),
    question("How many grams are in 1 kilogram?", 1000, "1 kilogram equals 1,000 grams."),
    question("What is 750 g + 250 g?", 1000, "750 + 250 = 1,000 grams, or 1 kilogram."),
    question("How many minutes pass from 2:15 to 3:00?", 45, "There are 45 minutes from :15 to the next hour."),
    question("A lesson lasts 90 minutes. How many minutes are left after 1 hour?", 30, "1 hour is 60 minutes, and 90 − 60 = 30."),
    question("How many 25-cent coins make $1.00?", 4, "4 groups of 25 cents make 100 cents."),
    question("Four equal snacks cost $2.00 altogether. How many cents does each snack cost?", 50, "200 cents ÷ 4 = 50 cents."),
    question("What is the value of three 20-cent coins, in cents?", 60, "3 × 20 = 60 cents."),
    question("A rectangle is 5 cm long and 3 cm wide. What is its perimeter?", 16, "Add all sides: 5 + 3 + 5 + 3."),
    question("A 12 cm strip is cut into pieces of 4 cm. How many pieces are made?", 3, "12 ÷ 4 = 3 pieces."),
    question("How many millilitres are in 1 litre?", 1000, "1 litre equals 1,000 millilitres."),
    question("What is 500 mL + 250 mL?", 750, "500 + 250 = 750 millilitres."),
    question("How many minutes pass from 9:40 to 10:10?", 30, "20 minutes to 10:00, then 10 more minutes."),

    question("How many sides does a triangle have?", 3, "A triangle has 3 sides."),
    question("How many sides does a rectangle have?", 4, "A rectangle has 4 sides."),
    question("How many sides does a pentagon have?", 5, "A pentagon has 5 sides."),
    question("How many corners does a circle have?", 0, "A circle has no corners."),
    question("What comes next: 2, 4, 6, 8, ___?", 10, "The pattern adds 2 each time."),
    question("What comes next: 15, 20, 25, 30, ___?", 35, "The pattern adds 5 each time."),
    question("What comes next: 100, 90, 80, ___?", 70, "The pattern subtracts 10 each time."),
    question("A class has 4 red counters and 6 blue counters. How many counters are there?", 10, "4 + 6 = 10 counters."),
    question("A chart shows 3 books on Monday, 5 on Tuesday, and 2 on Wednesday. How many books altogether?", 10, "3 + 5 + 2 = 10."),
    question("12 students form 2 equal teams. How many students are on each team?", 6, "12 ÷ 2 = 6."),
    question("How many faces does a cube have?", 6, "A cube has 6 flat faces."),
    question("A square has a side length of 4 cm. What is its perimeter?", 16, "4 equal sides: 4 + 4 + 4 + 4."),
    question("There are 3 rows of 5 stars. How many stars are there?", 15, "3 × 5 = 15 stars."),
    question("A grid has 4 rows of 6 squares. How many squares are there?", 24, "4 × 6 = 24 squares."),
    question("How many numbers are on an analogue clock face?", 12, "An analogue clock shows the numbers 1 through 12."),
    question("How many right angles make one full turn?", 4, "Four quarter turns make one full turn."),
    question("How many right angles make a half turn?", 2, "Two quarter turns make a half turn."),
    question("A chart shows 7 cats and 9 dogs. How many more dogs are there?", 2, "9 − 7 = 2 more dogs."),
    question("What comes next: 1, 4, 7, 10, ___?", 13, "The pattern adds 3 each time."),
    question("A shape has 4 equal sides and 4 corners. How many sides does it have?", 4, "The shape has 4 sides."),
  ];

  const dialog = document.getElementById("rumi-chat-dialog");
  const launcher = document.getElementById("rumi-chat-launcher");
  const closeButton = document.getElementById("rumi-chat-close");
  const messages = document.getElementById("rumi-chat-messages");
  const promptPanel = document.getElementById("rumi-chat-prompts");
  const promptList = document.getElementById("rumi-chat-prompt-list");
  const restartButton = document.getElementById("rumi-chat-restart");
  const mathLaunchButton = document.getElementById("rumi-math-launch");
  const mathQuest = document.getElementById("rumi-math-quest");
  const mathProgress = document.getElementById("rumi-math-progress");
  const mathQuestion = document.getElementById("rumi-math-question");
  const mathChoices = document.getElementById("rumi-math-choices");
  const mathFeedback = document.getElementById("rumi-math-feedback");
  const mathNextButton = document.getElementById("rumi-math-next");
  const mathExitButton = document.getElementById("rumi-math-exit");

  if (
    !dialog || !launcher || !closeButton || !messages || !promptPanel || !promptList || !restartButton
    || !mathLaunchButton || !mathQuest || !mathProgress || !mathQuestion || !mathChoices
    || !mathFeedback || !mathNextButton || !mathExitButton || mathQuestions.length !== 100
  ) {
    return;
  }

  const initialMessages = messages.innerHTML;
  let isResponding = false;
  let questionIndex = 0;
  let score = 0;
  let hasAnswered = false;

  const scrollMessagesToBottom = () => {
    messages.scrollTop = messages.scrollHeight;
  };

  const appendMessage = (speaker, text, variant) => {
    const message = document.createElement("article");
    const speakerElement = document.createElement("p");
    const textElement = document.createElement("p");

    message.className = `rumi-chat-message rumi-chat-message-${variant}`;
    speakerElement.className = "rumi-chat-speaker";
    speakerElement.textContent = speaker;
    textElement.textContent = text;
    message.append(speakerElement, textElement);
    messages.append(message);
    scrollMessagesToBottom();
  };

  const setPromptAvailability = (disabled) => {
    promptList.querySelectorAll("button").forEach((button) => {
      button.disabled = disabled;
    });
  };

  const respondToPrompt = (entry) => {
    if (isResponding) {
      return;
    }

    isResponding = true;
    setPromptAvailability(true);
    appendMessage("You", entry.prompt, "user");

    const typing = document.createElement("p");
    typing.className = "rumi-chat-typing";
    typing.textContent = "Rumi is thinking…";
    messages.append(typing);
    scrollMessagesToBottom();

    window.setTimeout(() => {
      typing.remove();
      appendMessage("Rumi", entry.reply, "rumi");
      isResponding = false;
      setPromptAvailability(false);
    }, 450);
  };

  const answerOptions = (answer, index) => {
    const options = [answer];
    const offsets = [1, -1, 2, -2, 5, -5, 10, -10, 20, -20, 100, -100];

    offsets.forEach((offset) => {
      const candidate = answer + (index % 2 === 0 ? offset : -offset);
      if (candidate >= 0 && !options.includes(candidate) && options.length < 4) {
        options.push(candidate);
      }
    });

    let fallback = 1;
    while (options.length < 4) {
      const candidate = answer + fallback;
      if (!options.includes(candidate)) {
        options.push(candidate);
      }
      fallback += 1;
    }

    return options.sort((left, right) => ((left * 31 + index * 17) % 101) - ((right * 31 + index * 17) % 101));
  };

  const showMathResult = (isCorrect, selectedAnswer) => {
    const currentQuestion = mathQuestions[questionIndex];
    const options = mathChoices.querySelectorAll("button");

    hasAnswered = true;
    options.forEach((button) => {
      const buttonAnswer = Number(button.dataset.answer);
      button.disabled = true;
      if (buttonAnswer === currentQuestion.answer) {
        button.classList.add("is-correct");
      } else if (buttonAnswer === selectedAnswer) {
        button.classList.add("is-incorrect");
      }
    });

    if (isCorrect) {
      score += 1;
      mathFeedback.textContent = `Rumi: That’s right, star. ${currentQuestion.explanation}`;
      mathFeedback.className = "rumi-math-feedback is-correct";
    } else {
      mathFeedback.textContent = `Rumi: Keep going. The answer is ${currentQuestion.answer}. ${currentQuestion.explanation}`;
      mathFeedback.className = "rumi-math-feedback is-incorrect";
    }

    mathProgress.textContent = `Question ${questionIndex + 1} of ${mathQuestions.length} · Score ${score}`;
    if (questionIndex === mathQuestions.length - 1) {
      mathNextButton.textContent = "See my result";
    } else {
      mathNextButton.textContent = "Next question";
    }
    mathNextButton.hidden = false;
  };

  const renderQuestion = () => {
    const currentQuestion = mathQuestions[questionIndex];

    hasAnswered = false;
    mathProgress.textContent = `Question ${questionIndex + 1} of ${mathQuestions.length} · Score ${score}`;
    mathQuestion.textContent = `Rumi asks: ${currentQuestion.prompt}`;
    mathFeedback.textContent = "";
    mathFeedback.className = "rumi-math-feedback";
    mathNextButton.hidden = true;
    mathChoices.innerHTML = "";

    answerOptions(currentQuestion.answer, questionIndex).forEach((answer) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "rumi-math-choice";
      button.dataset.answer = answer;
      button.textContent = answer;
      button.addEventListener("click", () => {
        if (!hasAnswered) {
          showMathResult(answer === currentQuestion.answer, answer);
        }
      });
      mathChoices.append(button);
    });
  };

  const finishMathQuest = () => {
    mathProgress.textContent = `Math Quest complete · Score ${score} of ${mathQuestions.length}`;
    mathQuestion.textContent = "Rumi: You completed all 100 questions. Every challenge you faced made you stronger.";
    mathChoices.innerHTML = "";
    mathFeedback.textContent = "Choose Back to chat to continue talking with Rumi, or start the quest again.";
    mathFeedback.className = "rumi-math-feedback is-correct";
    mathNextButton.hidden = true;
  };

  const startMathQuest = () => {
    questionIndex = 0;
    score = 0;
    messages.hidden = true;
    promptPanel.hidden = true;
    mathQuest.hidden = false;
    renderQuestion();
  };

  const exitMathQuest = () => {
    mathQuest.hidden = true;
    messages.hidden = false;
    promptPanel.hidden = false;
  };

  prompts.forEach((entry) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "rumi-chat-prompt";
    button.textContent = entry.prompt;
    button.addEventListener("click", () => respondToPrompt(entry));
    promptList.append(button);
  });

  launcher.addEventListener("click", () => {
    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }
    scrollMessagesToBottom();
  });

  closeButton.addEventListener("click", () => dialog.close());
  mathLaunchButton.addEventListener("click", startMathQuest);
  mathExitButton.addEventListener("click", exitMathQuest);

  mathNextButton.addEventListener("click", () => {
    if (questionIndex === mathQuestions.length - 1) {
      finishMathQuest();
      return;
    }
    questionIndex += 1;
    renderQuestion();
  });

  restartButton.addEventListener("click", () => {
    if (isResponding) {
      return;
    }
    messages.innerHTML = initialMessages;
    setPromptAvailability(false);
    scrollMessagesToBottom();
  });

  dialog.addEventListener("close", () => launcher.focus());
})();
