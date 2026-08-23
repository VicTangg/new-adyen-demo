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
  const buildBank = (topicFactories) => {
    const questions = [];
    for (let turn = 0; questions.length < 100; turn += 1) {
      topicFactories.forEach((makeQuestion) => {
        if (questions.length < 100) {
          questions.push(makeQuestion(turn));
        }
      });
    }
    return questions;
  };

  const gradeLevels = [
    {
      id: "pyp-1",
      label: "PYP 1",
      description: "Number sense, patterns, shapes, time, and simple data",
      build: () => buildBank([
        (i) => question(`What is ${1 + i} + ${2 + (i % 5)}?`, 3 + i + (i % 5), "Count forward from the first number."),
        (i) => question(`What is ${10 + i} − ${1 + (i % 5)}?`, 9 + i - (i % 5), "Count back from the larger number."),
        (i) => question(`What comes next: ${2 * i}, ${2 * i + 1}, ${2 * i + 2}, ___?`, 2 * i + 3, "This counting pattern goes up by 1."),
        (i) => {
          const number = 12 + i * 7;
          return question(`How many tens are in ${number}?`, Math.floor(number / 10), "Look at the tens digit.");
        },
        (i) => question(`What comes next when you count by 5s: ${5 * (i + 1)}, ${5 * (i + 2)}, ___?`, 5 * (i + 3), "Add 5 each time."),
        (i) => question(`How many sides does a shape with ${3 + i} sides have?`, 3 + i, "Count each straight side."),
        (i) => {
          const hour = i + 1;
          return question(`It is ${hour}:00. What hour will it be one hour later?`, hour === 12 ? 1 : hour + 1, "Move forward one hour on the clock.");
        },
        (i) => question(`A ribbon is ${5 + i} cm long. Another ribbon is 2 cm longer. How long is it?`, 7 + i, "Add 2 centimetres."),
        (i) => question(`A picture graph shows ${3 + i} stars on Monday and 2 stars on Tuesday. How many stars altogether?`, 5 + i, "Add the two groups."),
        (i) => question(`There are 2 groups of ${2 + i} counters. How many counters are there?`, 2 * (2 + i), "Add the two equal groups."),
      ]),
    },
    {
      id: "pyp-2",
      label: "PYP 2",
      description: "Place value, two-digit operations, grouping, money, and measurement",
      build: () => buildBank([
        (i) => {
          const number = 24 + i * 6;
          return question(`What is the value of the tens digit in ${number}?`, Math.floor(number / 10) * 10, "The tens digit tells how many groups of ten there are.");
        },
        (i) => question(`What is ${26 + i * 3} + ${14 + i}?`, 40 + i * 4, "Add the tens and ones."),
        (i) => question(`What is ${52 + i * 3} − ${10 + i}?`, 42 + i * 2, "Subtract tens, then ones."),
        (i) => question(`What is ${2 + i} groups of 5?`, (2 + i) * 5, "Count in fives."),
        (i) => question(`${18 + i * 2} counters are shared equally by 2 children. How many does each child get?`, 9 + i, "Split the counters into 2 equal groups."),
        (i) => question(`You have ${20 + i * 5} cents and spend 10 cents. How many cents remain?`, 10 + i * 5, "Subtract 10 cents."),
        (i) => question(`How many minutes are in ${2 + i} hours?`, (2 + i) * 60, "Each hour has 60 minutes."),
        (i) => question(`What is half of ${10 + i * 2}?`, 5 + i, "Split the number into 2 equal groups."),
        (i) => {
          const length = 3 + i;
          const width = 2 + (i % 4);
          return question(`A rectangle is ${length} cm by ${width} cm. What is its perimeter?`, 2 * (length + width), "Add all four sides.");
        },
        (i) => question(`A chart shows ${4 + i} red balloons and ${3 + i} blue balloons. How many balloons are there?`, 7 + i * 2, "Add both categories."),
      ]),
    },
    {
      id: "pyp-3",
      label: "PYP 3",
      description: "Three-digit operations, multiplication, fractions, geometry, and data",
      build: () => buildBank([
        (i) => question(`What is ${127 + i * 11} + ${34 + i * 3}?`, 161 + i * 14, "Add hundreds, tens, and ones."),
        (i) => question(`What is ${184 + i * 9} − ${29 + i * 2}?`, 155 + i * 7, "Subtract tens and ones carefully."),
        (i) => question(`What is ${3 + (i % 5)} × ${4 + (i % 3)}?`, (3 + (i % 5)) * (4 + (i % 3)), "Use equal groups or a multiplication fact."),
        (i) => {
          const divisor = 3 + i;
          const quotient = 4 + i;
          return question(`What is ${divisor * quotient} ÷ ${divisor}?`, quotient, "Use the related multiplication fact.");
        },
        (i) => question(`What is one quarter of ${8 + i * 4}?`, 2 + i, "Divide the total into 4 equal groups."),
        (i) => {
          const number = 234 + i * 53;
          return question(`What is the value of the hundreds digit in ${number}?`, Math.floor(number / 100) * 100, "Look at the digit in the hundreds place.");
        },
        (i) => {
          const length = 4 + i;
          const width = 3 + (i % 4);
          return question(`A rectangle is ${length} cm by ${width} cm. What is its area?`, length * width, "Multiply length by width.");
        },
        (i) => question(`How many minutes pass from ${1 + i}:15 to ${2 + i}:00?`, 45, "There are 45 minutes from :15 to the next hour."),
        (i) => {
          const middle = 6 + i;
          return question(`What is the mean of ${middle - 2}, ${middle}, and ${middle + 2}?`, middle, "The numbers balance around the middle value.");
        },
        (i) => question(`How many centimetres are in ${2 + i} metres?`, (2 + i) * 100, "Each metre has 100 centimetres."),
      ]),
    },
    {
      id: "pyp-4",
      label: "PYP 4",
      description: "Large numbers, fractions, decimals, coordinates, and area",
      build: () => buildBank([
        (i) => {
          const number = 1234 + i * 321;
          return question(`What is the value of the thousands digit in ${number}?`, Math.floor(number / 1000) * 1000, "The first digit shows the number of thousands.");
        },
        (i) => question(`What is ${1245 + i * 37} + ${638 + i * 12}?`, 1883 + i * 49, "Regroup if a place value total is 10 or more."),
        (i) => question(`What is ${2000 + i * 83} − ${745 + i * 13}?`, 1255 + i * 70, "Subtract by place value."),
        (i) => question(`What is ${12 + i} × ${3 + (i % 4)}?`, (12 + i) * (3 + (i % 4)), "Break the first factor into tens and ones."),
        (i) => {
          const divisor = 4 + (i % 5);
          const quotient = 12 + i;
          return question(`What is ${divisor * quotient} ÷ ${divisor}?`, quotient, "Division undoes multiplication.");
        },
        (i) => {
          const wholes = i + 1;
          return question(`How many eighths are in ${wholes} whole ${wholes === 1 ? "number" : "numbers"}?`, wholes * 8, "Each whole is split into 8 equal parts called eighths.");
        },
        (i) => question(`How many tenths are in ${3 + i} whole numbers?`, (3 + i) * 10, "Each whole has 10 tenths."),
        (i) => {
          const length = 6 + i;
          const width = 4 + (i % 4);
          return question(`A rectangle is ${length} cm by ${width} cm. What is its area?`, length * width, "Multiply length by width.");
        },
        (i) => {
          const x = 2 + i;
          const move = 3 + (i % 4);
          return question(`A point has x-coordinate ${x}. It moves ${move} units right. What is its new x-coordinate?`, x + move, "Moving right increases the x-coordinate.");
        },
        (i) => question(`A bar graph shows ${8 + i} votes for A and ${5 + i} votes for B. How many more votes did A receive?`, 3, "Subtract the smaller bar from the taller bar."),
      ]),
    },
    {
      id: "pyp-5",
      label: "PYP 5",
      description: "Factors, decimals, percentages, volume, coordinates, and statistics",
      build: () => buildBank([
        (i) => question(`What is ${14 + i} × ${4 + (i % 3)}?`, (14 + i) * (4 + (i % 3)), "Use multiplication strategies with tens and ones."),
        (i) => {
          const divisor = 6 + (i % 4);
          const quotient = 15 + i;
          return question(`What is ${divisor * quotient} ÷ ${divisor}?`, quotient, "Use the inverse operation.");
        },
        (i) => {
          const factor = 6 + i;
          const a = 3 * factor;
          const b = 5 * factor;
          return question(`What is the greatest common factor of ${a} and ${b}?`, factor, "The largest shared factor is the common scale factor.");
        },
        (i) => question(`What is one fifth of ${25 + i * 5}?`, 5 + i, "Divide the total into 5 equal groups."),
        (i) => question(`What is 25% of ${40 + i * 4}?`, 10 + i, "25% is one quarter."),
        (i) => question(`What is ${3 + i}.4 + 2.6?`, 6 + i, "The tenths make one more whole."),
        (i) => {
          const base = 8 + i * 2;
          const height = 4 + (i % 4) * 2;
          return question(`A triangle has base ${base} cm and height ${height} cm. What is its area?`, base * height / 2, "Triangle area is base × height ÷ 2.");
        },
        (i) => {
          const edge = 2 + i;
          return question(`A cube has edge length ${edge} cm. What is its volume?`, edge ** 3, "Multiply edge × edge × edge.");
        },
        (i) => {
          const x = 4 + i;
          const distance = 3 + (i % 5);
          return question(`Two points are ${distance} units apart horizontally. If one x-coordinate is ${x}, what is the other x-coordinate to the right?`, x + distance, "Add the horizontal distance.");
        },
        (i) => {
          const mean = 10 + i;
          return question(`What is the mean of ${mean - 3}, ${mean}, and ${mean + 3}?`, mean, "The values balance around the mean.");
        },
      ]),
    },
    {
      id: "myp-1",
      label: "MYP 1",
      description: "Integers, ratios, algebra, geometry, probability, and data",
      build: () => buildBank([
        (i) => question(`What is ${-8 + i} + ${5 + i}?`, -3 + i * 2, "Add a positive integer to a negative integer."),
        (i) => question(`In a 2:3 ratio, the first part is ${2 * (i + 2)}. What is the second part?`, 3 * (i + 2), "Multiply the scale factor by 3."),
        (i) => question(`What is 20% of ${40 + i * 5}?`, 8 + i, "Twenty percent is one fifth."),
        (i) => {
          const answer = 3 + i;
          return question(`Solve: 2x + 4 = ${2 * answer + 4}. What is x?`, answer, "Subtract 4, then divide by 2.");
        },
        (i) => question(`What is the next term: ${4 + i}, ${7 + i}, ${10 + i}, ___?`, 13 + i, "The sequence increases by 3."),
        (i) => {
          const first = 40 + i;
          const second = 60 + i;
          return question(`Two angles in a triangle are ${first}° and ${second}°. What is the third angle?`, 180 - first - second, "Angles in a triangle total 180°.");
        },
        (i) => {
          const length = 5 + i;
          const width = 3 + (i % 4);
          return question(`What is the area of a ${length} cm by ${width} cm rectangle?`, length * width, "Area is length × width.");
        },
        (i) => question(`A bag has ${3 + i} red counters and ${7 + i} counters altogether. What percent are red?`, (3 + i) * 100 / (7 + i), "Red counters ÷ total counters × 100."),
        (i) => {
          const middle = 8 + i;
          return question(`What is the median of ${middle - 2}, ${middle}, ${middle + 2}?`, middle, "The median is the middle value when ordered.");
        },
        (i) => {
          const x = -4 + i;
          const move = 5;
          return question(`A point has x-coordinate ${x}. It moves ${move} units right. What is the new x-coordinate?`, x + move, "Moving right adds to x.");
        },
      ]),
    },
    {
      id: "myp-2",
      label: "MYP 2",
      description: "Percentages, equations, functions, Pythagoras, and statistics",
      build: () => buildBank([
        (i) => {
          const original = 40 + i * 10;
          return question(`Increase ${original} by 10%. What is the new value?`, original * 1.1, "10% is one tenth of the original value.");
        },
        (i) => {
          const scale = 2 + i;
          return question(`Simplify ${4 * scale}:${6 * scale}. What is the first simplified term?`, 2, "Divide both parts by their common factor.");
        },
        (i) => {
          const answer = 4 + i;
          return question(`Solve: 3x − 5 = ${3 * answer - 5}. What is x?`, answer, "Add 5, then divide by 3.");
        },
        (i) => {
          const x = 2 + i;
          return question(`For y = 3x + 2, what is y when x = ${x}?`, 3 * x + 2, "Substitute the value of x.");
        },
        (i) => {
          const triples = [[3, 4, 5], [5, 12, 13], [8, 15, 17], [7, 24, 25], [9, 12, 15]];
          const scale = 1 + Math.floor(i / triples.length);
          const [baseA, baseB, baseC] = triples[i % triples.length];
          const [a, b, c] = [baseA * scale, baseB * scale, baseC * scale];
          return question(`A right triangle has legs ${a} and ${b}. What is the hypotenuse?`, c, "Use a² + b² = c².");
        },
        (i) => {
          const x = 2 + i;
          return question(`A point at x = ${x} is reflected in the y-axis. What is its new x-coordinate?`, -x, "Reflection in the y-axis changes the sign of x.");
        },
        (i) => {
          const numerator = 2 + i;
          const denominator = numerator + 8;
          return question(`What is ${numerator}/${denominator} + 8/${denominator}?`, 1, "The numerators add to the denominator, which is one whole.");
        },
        (i) => {
          const goldSections = i + 1;
          const totalSections = goldSections * 4;
          return question(`A spinner has ${totalSections} equal sections and ${goldSections} are gold. What is the chance of gold as a percent?`, 25, "One out of every four equal sections is gold.");
        },
        (i) => {
          const mean = 12 + i;
          return question(`The mean of 3 scores is ${mean}. What is their total?`, mean * 3, "Mean × number of scores = total.");
        },
        (i) => question(`What comes next: ${5 + i}, ${9 + i}, ${13 + i}, ___?`, 17 + i, "The sequence increases by 4."),
      ]),
    },
    {
      id: "myp-3",
      label: "MYP 3",
      description: "Indices, linear and quadratic relationships, circles, and probability",
      build: () => buildBank([
        (i) => question(`What is 2 to the power of ${3 + i}?`, 2 ** (3 + i), "Multiply 2 by itself for the number of factors shown."),
        (i) => question(`What is 3 × 10 to the power of ${3 + i}?`, 3 * 10 ** (3 + i), "Move the decimal place right for each power of 10."),
        (i) => {
          const answer = 5 + i;
          return question(`Solve: 4x + 3 = ${4 * answer + 3}. What is x?`, answer, "Subtract 3, then divide by 4.");
        },
        (i) => {
          const root = 2 + i;
          return question(`What is the positive solution of x² = ${root ** 2}?`, root, "Take the positive square root.");
        },
        (i) => {
          const x = 3 + i;
          const y = 2 + (i % 5);
          return question(`Solve x + y = ${x + y} and x − y = ${x - y}. What is x?`, x, "Add the equations to find 2x.");
        },
        (i) => {
          const x = 2 + i;
          return question(`For y = 2x − 1, what is y when x = ${x}?`, 2 * x - 1, "Substitute x into the rule.");
        },
        (i) => {
          const triples = [[5, 12, 13], [8, 15, 17], [7, 24, 25], [9, 12, 15], [20, 21, 29]];
          const scale = 1 + Math.floor(i / triples.length);
          const [baseA, baseB, baseC] = triples[i % triples.length];
          const [a, b, c] = [baseA * scale, baseB * scale, baseC * scale];
          return question(`A right triangle has legs ${a} and ${b}. What is its hypotenuse?`, c, "Use Pythagoras' theorem.");
        },
        (i) => {
          const radius = 7 * (i + 1);
          return question(`Using π = 22/7, what is the circumference of a circle with radius ${radius}?`, 2 * 22 / 7 * radius, "Circumference is 2πr.");
        },
        (i) => {
          const blue = i + 1;
          const green = i + 1;
          return question(`A bag has ${blue} blue counters and ${green} green counters. What percent chance is there of picking blue?`, 50, "Blue is half of the equally sized total.");
        },
        (i) => {
          const middle = 15 + i;
          return question(`What is the median of ${middle - 4}, ${middle - 2}, ${middle}, ${middle + 2}, ${middle + 4}?`, middle, "The ordered middle value is the median.");
        },
      ]),
    },
    {
      id: "myp-4",
      label: "MYP 4",
      description: "Quadratics, trigonometry, finance, vectors, and probability",
      build: () => buildBank([
        (i) => {
          const root1 = 2 + i;
          const root2 = 5 + i;
          return question(`What is the smaller root of (x − ${root1})(x − ${root2}) = 0?`, root1, "Set each factor equal to zero.");
        },
        (i) => {
          const x = 2 + i;
          return question(`For y = x² − 3x + 2, what is y when x = ${x}?`, x ** 2 - 3 * x + 2, "Substitute x and follow the order of operations.");
        },
        (i) => {
          const triples = [[3, 4, 5], [5, 12, 13], [8, 15, 17], [7, 24, 25], [9, 12, 15]];
          const scale = 1 + Math.floor(i / triples.length);
          const [baseOpposite, baseAdjacent, baseHypotenuse] = triples[i % triples.length];
          const [opposite, adjacent, hypotenuse] = [baseOpposite * scale, baseAdjacent * scale, baseHypotenuse * scale];
          return question(`In a right triangle, the adjacent side is ${adjacent} and hypotenuse is ${hypotenuse}. What is the opposite side?`, opposite, "Use a² + b² = c².");
        },
        (i) => question(`What is 3 to the power of ${2 + i}?`, 3 ** (2 + i), "Multiply 3 by itself for the exponent."),
        (i) => {
          const principal = 100 + i * 20;
          return question(`A savings account has ${principal} dollars and grows by 10% once. What is the new amount?`, principal * 1.1, "Add one tenth of the original amount.");
        },
        (i) => {
          const a = 2 + i;
          const b = 3;
          return question(`What is the dot product of vectors (${a}, ${b}) and (2, 1)?`, a * 2 + b, "Multiply matching components, then add.");
        },
        (i) => {
          const radius = 7 * (i + 1);
          return question(`Using π = 22/7, what is the area of a circle with radius ${radius}?`, 22 / 7 * radius ** 2, "Area is πr².");
        },
        (i) => {
          const original = 80 + i * 4;
          return question(`Decrease ${original} by 25%. What is the new value?`, original * 0.75, "Subtract one quarter of the original value.");
        },
        (i) => {
          const n = 4 + i;
          return question(`How many pairs can be made from ${n} different objects?`, n * (n - 1) / 2, "Use n(n − 1) ÷ 2.");
        },
        (i) => {
          const x = 1 + i;
          return question(`For y = 4x − 3, what is y when x = ${x}?`, 4 * x - 3, "Substitute x into the linear rule.");
        },
      ]),
    },
    {
      id: "myp-5",
      label: "MYP 5",
      description: "Functions, logarithms, sequences, vectors, finance, and modelling",
      build: () => buildBank([
        (i) => {
          const x = 2 + i;
          return question(`If f(x) = 2x + 1 and g(x) = x + 3, what is f(g(${x}))?`, 2 * (x + 3) + 1, "Evaluate g first, then use that answer in f.");
        },
        (i) => question(`What is log base 2 of ${2 ** (2 + i)}?`, 2 + i, "A logarithm asks for the exponent."),
        (i) => {
          const first = 3 + i;
          return question(`What is the 10th term of the sequence ${first}, ${first + 4}, ${first + 8}, ...?`, first + 36, "The sequence adds 4; move forward 9 times.");
        },
        (i) => {
          const x = 4 + i;
          const y = 2 + (i % 4);
          return question(`Solve x + y = ${x + y} and x − y = ${x - y}. What is y?`, y, "Subtract the second equation from the first to find 2y.");
        },
        (i) => {
          const vertexX = -3 + i;
          return question(`For y = (x − ${vertexX})² + 4, what is the x-coordinate of the vertex?`, vertexX, "The vertex is at x = the value inside the bracket.");
        },
        (i) => {
          const opposite = 3 + i;
          const adjacent = 4;
          return question(`A right triangle has opposite side ${opposite} and adjacent side ${adjacent}. What is tan θ as a numerator when tan θ = opposite/adjacent?`, opposite, "Tangent is opposite ÷ adjacent.");
        },
        (i) => {
          const triples = [[3, 4, 5], [5, 12, 13], [8, 15, 17], [7, 24, 25], [9, 12, 15]];
          const scale = 1 + Math.floor(i / triples.length);
          const [baseX, baseY, baseMagnitude] = triples[i % triples.length];
          const [x, y, magnitude] = [baseX * scale, baseY * scale, baseMagnitude * scale];
          return question(`What is the magnitude of vector (${x}, ${y})?`, magnitude, "Magnitude is √(x² + y²).");
        },
        (i) => {
          const principal = 200 + i * 50;
          return question(`What is 5% simple interest on ${principal} dollars for one year?`, principal * 0.05, "Find five hundredths of the principal.");
        },
        (i) => {
          const scale = i + 1;
          return question(`A group has ${6 * scale} girls and ${4 * scale} boys. What percent of the group are girls?`, 60, "6 out of 10 is 60%.");
        },
        (i) => question(`What is 5 × 10 to the power of ${2 + i}?`, 5 * 10 ** (2 + i), "Use the exponent to move the place value."),
      ]),
    },
    {
      id: "dp-1",
      label: "DP 1",
      description: "Functions, calculus foundations, trigonometry, vectors, and probability",
      build: () => buildBank([
        (i) => {
          const x = 1 + i;
          return question(`For f(x) = x² + 2x − 1, what is f(${x})?`, x ** 2 + 2 * x - 1, "Substitute x into the function.");
        },
        (i) => {
          const root1 = 2 + i;
          const root2 = 6 + i;
          return question(`What is the larger root of (x − ${root1})(x − ${root2}) = 0?`, root2, "Set each factor equal to zero.");
        },
        (i) => question(`What is log base 10 of ${10 ** (2 + i)}?`, 2 + i, "The answer is the exponent on 10."),
        (i) => {
          const coefficient = 2 + (i % 5);
          const x = 1 + i;
          return question(`For y = ${coefficient}x² + 3x, what is dy/dx when x = ${x}?`, 2 * coefficient * x + 3, "Differentiate to get 2ax + 3, then substitute x.");
        },
        (i) => {
          const coefficient = 2;
          const x = 2 + i;
          return question(`What is the definite integral of ${coefficient}x from 0 to ${x}?`, coefficient * x ** 2 / 2, "The antiderivative is ax²/2.");
        },
        (i) => question(`What is 30% of ${100 + i * 20}?`, 30 + i * 6, "Thirty percent is three tenths."),
        (i) => {
          const a = 2 + i;
          const b = 4;
          return question(`What is the dot product of (${a}, ${b}) and (3, 2)?`, a * 3 + b * 2, "Multiply matching components, then add.");
        },
        (i) => {
          const base = 2 + i;
          return question(`What is the coefficient of x² in (x + ${base})³?`, 3 * base, "The x² term is 3bx².");
        },
        (i) => {
          const mean = 20 + i;
          return question(`Four values have a mean of ${mean}. What is their total?`, mean * 4, "Mean × number of values = total.");
        },
        (i) => {
          const initial = 50 + i * 10;
          return question(`An amount of ${initial} grows by 20% once. What is the new amount?`, initial * 1.2, "Multiply by 1.2.");
        },
      ]),
    },
    {
      id: "dp-2",
      label: "DP 2",
      description: "Advanced functions, calculus, vectors, complex numbers, and modelling",
      build: () => buildBank([
        (i) => {
          const value = 14 + i * 3;
          return question(`If f(x) = 3x + 2, what is f⁻¹(${value})?`, (value - 2) / 3, "Undo +2, then divide by 3.");
        },
        (i) => {
          const coefficient = 3 + (i % 4);
          const x = 1 + i;
          return question(`For y = ${coefficient}x³ − 2x, what is dy/dx when x = ${x}?`, 3 * coefficient * x ** 2 - 2, "Differentiate to get 3ax² − 2.");
        },
        (i) => {
          const coefficient = 3;
          const x = 2 + i;
          return question(`What is the definite integral of ${coefficient}x² from 0 to ${x}?`, coefficient * x ** 3 / 3, "The antiderivative is ax³/3.");
        },
        (i) => {
          const coefficient = 2 + (i % 4);
          const x = 1 + i;
          return question(`For y = ${coefficient}x³, what is d²y/dx² when x = ${x}?`, 6 * coefficient * x, "Differentiate twice: 6ax.");
        },
        (i) => {
          const a = 3 + i;
          const b = 4;
          return question(`What is the dot product of vectors (${a}, ${b}) and (2, −1)?`, a * 2 - b, "Multiply matching components, then add.");
        },
        (i) => question(`What is the real part of (3 + ${4 + i}i) + (2 − 5i)?`, 5, "Add the real parts: 3 + 2."),
        (i) => {
          const tenths = i + 1;
          return question(`An event has probability ${tenths / 10}. What is that probability as a percent?`, tenths * 10, "Multiply the decimal by 100.");
        },
        (i) => {
          const first = 2 + i;
          return question(`A geometric sequence starts ${first}, ${first * 3}, ${first * 9}. What is the next term?`, first * 27, "Multiply by 3 each time.");
        },
        (i) => {
          const a = 2 + (i % 4);
          const b = 3 + (i % 5);
          const c = 1 + (i % 3);
          const d = 4 + (i % 4);
          return question(`What is the determinant of [[${a}, ${b}], [${c}, ${d}]]?`, a * d - b * c, "For a 2×2 matrix, determinant is ad − bc.");
        },
        (i) => {
          const vertex = 1 + i;
          return question(`For y = (x − ${vertex})² − 6, at what x-value is y smallest?`, vertex, "The square term is smallest when it equals zero.");
        },
      ]),
    },
  ];

  const dialog = document.getElementById("rumi-chat-dialog");
  const launcher = document.getElementById("rumi-chat-launcher");
  const closeButton = document.getElementById("rumi-chat-close");
  const messages = document.getElementById("rumi-chat-messages");
  const promptPanel = document.getElementById("rumi-chat-prompts");
  const promptList = document.getElementById("rumi-chat-prompt-list");
  const restartButton = document.getElementById("rumi-chat-restart");
  const mathLaunchButton = document.getElementById("rumi-math-launch");
  const gradePicker = document.getElementById("rumi-math-grade-picker");
  const gradeList = document.getElementById("rumi-math-grade-list");
  const gradeExitButton = document.getElementById("rumi-math-grade-exit");
  const mathQuest = document.getElementById("rumi-math-quest");
  const mathLevel = document.getElementById("rumi-math-level");
  const mathProgress = document.getElementById("rumi-math-progress");
  const mathQuestion = document.getElementById("rumi-math-question");
  const mathChoices = document.getElementById("rumi-math-choices");
  const mathFeedback = document.getElementById("rumi-math-feedback");
  const mathNextButton = document.getElementById("rumi-math-next");
  const mathRestartButton = document.getElementById("rumi-math-restart");
  const mathChangeGradeButton = document.getElementById("rumi-math-change-grade");
  const mathExitButton = document.getElementById("rumi-math-exit");
  const galleryImages = typeof document.querySelectorAll === "function"
    ? document.querySelectorAll(".hana-gallery img")
    : [];

  const mathControlsReady = Boolean(
    mathLaunchButton && gradePicker && gradeList && gradeExitButton && mathQuest && mathLevel
    && mathProgress && mathQuestion && mathChoices && mathFeedback && mathNextButton
    && mathRestartButton && mathChangeGradeButton && mathExitButton && gradeLevels.length === 12,
  );
  const legacyMathControlsReady = Boolean(
    mathLaunchButton && mathQuest && mathProgress && mathQuestion && mathChoices
    && mathFeedback && mathNextButton && mathExitButton,
  );

  const scrollMessagesToBottom = () => {
    if (messages) {
      messages.scrollTop = messages.scrollHeight;
    }
  };

  const openChat = () => {
    dialog.removeAttribute("hidden");
    try {
      if (typeof dialog.showModal === "function") {
        if (!dialog.open) {
          dialog.showModal();
        }
      } else {
        dialog.setAttribute("open", "");
      }
    } catch {
      dialog.setAttribute("open", "");
    }
    scrollMessagesToBottom();
  };

  const closeChat = () => {
    if (typeof dialog.close === "function" && dialog.open) {
      dialog.close();
    } else {
      dialog.removeAttribute("open");
    }
  };

  if (!dialog || !launcher) {
    return;
  }

  launcher.addEventListener("click", openChat);
  if (closeButton) {
    closeButton.addEventListener("click", closeChat);
  }
  dialog.addEventListener("close", () => launcher.focus());

  if (!messages || !promptPanel || !promptList || !restartButton) {
    return;
  }

  galleryImages.forEach((image) => {
    image.addEventListener("error", () => {
      const retries = Number(image.dataset.retryCount || 0);
      if (retries >= 2) {
        return;
      }

      image.dataset.retryCount = String(retries + 1);
      window.setTimeout(() => {
        const retryUrl = new URL(image.src, window.location.href);
        retryUrl.searchParams.set("retry", String(retries + 1));
        image.src = retryUrl.toString();
      }, 750 * (retries + 1));
    });
  });

  const initialMessages = messages.innerHTML;
  const questionBanks = new Map();
  let isResponding = false;
  let selectedLevel = null;
  let mathQuestions = [];
  let questionIndex = 0;
  let score = 0;
  let hasAnswered = false;

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

  const getQuestionBank = (level) => {
    if (!questionBanks.has(level.id)) {
      const bank = level.build();
      if (bank.length !== 100) {
        throw new Error(`${level.label} must contain exactly 100 questions.`);
      }
      questionBanks.set(level.id, bank);
    }
    return questionBanks.get(level.id);
  };

  const answerOptions = (answer, index) => {
    const options = [answer];
    const offsets = [1, -1, 2, -2, 5, -5, 10, -10, 20, -20, 100, -100];

    offsets.forEach((offset) => {
      const candidate = answer + (index % 2 === 0 ? offset : -offset);
      if (!options.includes(candidate) && options.length < 4) {
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

  const formatAnswer = (answer) => Number.isInteger(answer) ? String(answer) : String(Number(answer.toFixed(2)));

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
      mathFeedback.textContent = `Rumi: Keep going. The answer is ${formatAnswer(currentQuestion.answer)}. ${currentQuestion.explanation}`;
      mathFeedback.className = "rumi-math-feedback is-incorrect";
    }

    mathProgress.textContent = `${selectedLevel.label} · Question ${questionIndex + 1} of ${mathQuestions.length} · Score ${score}`;
    mathNextButton.textContent = questionIndex === mathQuestions.length - 1 ? "See my result" : "Next question";
    mathNextButton.hidden = false;
  };

  const renderQuestion = () => {
    const currentQuestion = mathQuestions[questionIndex];

    hasAnswered = false;
    mathProgress.textContent = `${selectedLevel.label} · Question ${questionIndex + 1} of ${mathQuestions.length} · Score ${score}`;
    mathQuestion.textContent = `Rumi asks: ${currentQuestion.prompt}`;
    mathFeedback.textContent = "";
    mathFeedback.className = "rumi-math-feedback";
    mathNextButton.hidden = true;
    if (mathRestartButton) {
      mathRestartButton.hidden = true;
    }
    mathChoices.innerHTML = "";

    answerOptions(currentQuestion.answer, questionIndex).forEach((answer) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "rumi-math-choice";
      button.dataset.answer = answer;
      button.textContent = formatAnswer(answer);
      button.addEventListener("click", () => {
        if (!hasAnswered) {
          showMathResult(answer === currentQuestion.answer, answer);
        }
      });
      mathChoices.append(button);
    });
  };

  const finishMathQuest = () => {
    mathProgress.textContent = `${selectedLevel.label} complete · Score ${score} of ${mathQuestions.length}`;
    mathQuestion.textContent = `Rumi: You completed all 100 ${selectedLevel.label} questions. Every challenge you faced made you stronger.`;
    mathChoices.innerHTML = "";
    mathFeedback.textContent = mathRestartButton
      ? "Restart this level, choose another level, or return to chat."
      : "Choose Back to chat to continue talking with Rumi, or start the quest again.";
    mathFeedback.className = "rumi-math-feedback is-correct";
    mathNextButton.hidden = true;
    if (mathRestartButton) {
      mathRestartButton.hidden = false;
    }
  };

  const selectLevel = (level) => {
    selectedLevel = level;
    mathQuestions = getQuestionBank(level);
    questionIndex = 0;
    score = 0;
    if (mathLevel) {
      mathLevel.textContent = `Rumi’s ${level.label} Math Quest`;
    }
    if (gradePicker) {
      gradePicker.hidden = true;
    }
    mathQuest.hidden = false;
    renderQuestion();
  };

  const startLegacyMathQuest = () => {
    messages.hidden = true;
    promptPanel.hidden = true;
    selectLevel(gradeLevels.find((level) => level.id === "pyp-3"));
  };

  const showGradePicker = () => {
    messages.hidden = true;
    promptPanel.hidden = true;
    mathQuest.hidden = true;
    gradePicker.hidden = false;
  };

  const exitMathQuest = () => {
    selectedLevel = null;
    mathQuestions = [];
    if (gradePicker) {
      gradePicker.hidden = true;
    }
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

  restartButton.addEventListener("click", () => {
    if (isResponding) {
      return;
    }
    messages.innerHTML = initialMessages;
    setPromptAvailability(false);
    scrollMessagesToBottom();
  });

  if (!legacyMathControlsReady) {
    return;
  }

  if (mathControlsReady) {
    gradeLevels.forEach((level) => {
      const button = document.createElement("button");
      const detail = document.createElement("span");

      button.type = "button";
      button.className = "rumi-math-grade";
      button.append(document.createTextNode(level.label));
      detail.textContent = level.description;
      button.append(detail);
      button.addEventListener("click", () => selectLevel(level));
      gradeList.append(button);
    });

    mathLaunchButton.addEventListener("click", showGradePicker);
    gradeExitButton.addEventListener("click", exitMathQuest);
    mathChangeGradeButton.addEventListener("click", showGradePicker);
    mathRestartButton.addEventListener("click", () => selectLevel(selectedLevel));
  } else {
    mathLaunchButton.addEventListener("click", startLegacyMathQuest);
  }

  mathExitButton.addEventListener("click", exitMathQuest);

  mathNextButton.addEventListener("click", () => {
    if (questionIndex === mathQuestions.length - 1) {
      finishMathQuest();
      return;
    }
    questionIndex += 1;
    renderQuestion();
  });
})();
