import axios from "axios";

// Must match the variables the scanner (python/app.py) actually computes
// per stock, and the operators evaluate_condition() understands.
const ALLOWED_VARIABLES = [
  "curr_open",
  "curr_close",
  "curr_low",
  "prev_close",
  "prev_low",
  "volume",
  "pe_ratio",
  "percent_gain",
  "sentiment_score",
];

const ALLOWED_OPERATORS = ["<", ">", "<=", ">=", "=="];
const ALLOWED_CONNECTORS = ["and", "or"];

const SYSTEM_PROMPT = `You convert a trader's plain-English stock-scanning strategy into a strict JSON array of conditions.

Each condition object has exactly these fields:
- "lhs": one of ${JSON.stringify(ALLOWED_VARIABLES)}
- "op": one of ${JSON.stringify(ALLOWED_OPERATORS)}
- "rhs": EITHER one of ${JSON.stringify(ALLOWED_VARIABLES)} (to compare two fields) OR a literal number (to compare against a fixed threshold, e.g. sentiment_score > 0.2, volume > 1000000)
- "conn": one of ${JSON.stringify(ALLOWED_CONNECTORS)} — the connector to the NEXT condition in the list (ignored/omit on the last condition)

Field meanings:
- curr_open / curr_close / curr_low: today's open, close, low price
- prev_close / prev_low: previous session's close, low price
- volume: today's traded volume
- pe_ratio: trailing P/E ratio
- percent_gain: percent change from today's open to today's close
- sentiment_score: average news sentiment for the stock, ranges from -1 (very negative) to 1 (very positive), 0 is neutral. Use this whenever the user mentions "sentiment", "news", "bullish", "bearish", "positive/negative news", etc.

Rules:
- Output ONLY a raw JSON array, no prose, no markdown fences, no explanation.
- Keep the array as short as possible while capturing the user's intent.
- When the user gives a vague sentiment threshold like "good sentiment" or "positive sentiment" without a number, use a reasonable default: 0.2 for "positive/good", -0.2 for "negative/bad", 0.5 for "strongly positive", -0.5 for "strongly negative".
- If the request is nonsensical or has nothing to do with a stock condition, return an empty array [].

Example input: "buy when today's close is higher than yesterday's close and news sentiment is positive"
Example output: [{"lhs":"curr_close","op":">","rhs":"prev_close","conn":"and"},{"lhs":"sentiment_score","op":">","rhs":0.2,"conn":"and"}]`;

function isValidCondition(cond) {
  if (!cond || typeof cond !== "object") return false;
  if (!ALLOWED_VARIABLES.includes(cond.lhs)) return false;
  if (!ALLOWED_OPERATORS.includes(cond.op)) return false;

  const rhsIsNumber = typeof cond.rhs === "number" && Number.isFinite(cond.rhs);
  const rhsIsVariable = ALLOWED_VARIABLES.includes(cond.rhs);
  if (!rhsIsNumber && !rhsIsVariable) return false;

  if (cond.conn !== undefined && !ALLOWED_CONNECTORS.includes(cond.conn)) {
    return false;
  }

  return true;
}

export const parseConditionsFromText = async (req, res) => {
  try {
    const { text } = req.body;

    if (!text || typeof text !== "string" || !text.trim()) {
      return res.status(400).json({
        success: false,
        message: "text_required",
      });
    }

    if (!process.env.GROQ_API_KEY) {
      return res.status(500).json({
        success: false,
        message: "GROQ_API_KEY not configured on server",
      });
    }

    const response = await axios.post(
      "https://api.groq.com/openai/v1/chat/completions",
      {
        model: "llama-3.3-70b-versatile",
        temperature: 0,
        response_format: { type: "json_object" },
        messages: [
          {
            role: "system",
            // Groq's json_object mode requires the wrapper object shape below,
            // so we ask for { "conditions": [...] } instead of a bare array.
            content: `${SYSTEM_PROMPT}\n\nRespond with a single JSON object of the exact shape {"conditions": [...]}, where "conditions" is the array described above. Do not add any other keys.`,
          },
          { role: "user", content: text.trim() },
        ],
      },
      {
        headers: {
          Authorization: `Bearer ${process.env.GROQ_API_KEY}`,
          "content-type": "application/json",
        },
        timeout: 20000,
      }
    );

    const rawText = response.data?.choices?.[0]?.message?.content?.trim();

    if (!rawText) {
      return res.status(502).json({
        success: false,
        message: "empty_model_response",
      });
    }

    // Strip accidental markdown fences just in case.
    const cleaned = rawText.replace(/^```json\s*|^```\s*|```$/g, "").trim();

    let parsed;
    try {
      parsed = JSON.parse(cleaned);
    } catch (err) {
      console.error("NLP parse: model did not return valid JSON:", rawText);
      return res.status(502).json({
        success: false,
        message: "model_returned_invalid_json",
      });
    }

    const conditionsArray = Array.isArray(parsed)
      ? parsed
      : Array.isArray(parsed?.conditions)
      ? parsed.conditions
      : null;

    if (!conditionsArray) {
      return res.status(502).json({
        success: false,
        message: "model_response_not_an_array",
      });
    }

    const validConditions = conditionsArray.filter(isValidCondition);

    if (validConditions.length === 0) {
      return res.status(422).json({
        success: false,
        message: "no_valid_conditions_extracted",
      });
    }

    // Assign fresh ids + enabled flag expected by the frontend's Condition shape.
    let nextId = Date.now();
    const conditions = validConditions.map((c) => ({
      id: nextId++,
      enabled: true,
      lhs: c.lhs,
      op: c.op,
      rhs: c.rhs,
      conn: c.conn && ALLOWED_CONNECTORS.includes(c.conn) ? c.conn : "and",
    }));

    return res.json({ success: true, conditions });
  } catch (error) {
    console.error("NLP conditions parse error:", error.response?.data || error.message);
    return res.status(500).json({
      success: false,
      message: "parse_failed",
    });
  }
};