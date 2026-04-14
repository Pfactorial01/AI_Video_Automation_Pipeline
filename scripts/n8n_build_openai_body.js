// Build OpenAI chat/completions body (json_schema). No credentials here — OpenAI is called by the HTTP Request node.
// SCHEMA injected by scripts/build_n8n_workflow.py
const SCHEMA = __INJECT_SCHEMA__;

const cfg = $input.first().json;
const topic = cfg.topic;

const openaiBody = {
  model: 'gpt-4o-mini',
  messages: [
    {
      role: 'system',
      content:
        'You are a documentary scriptwriter for a faceless YouTube channel. Output must match the JSON schema. Use cinematic, desaturated documentary tone. Keep scene count reasonable (e.g. at most 8 scenes).',
    },
    {
      role: 'user',
      content: `Topic: ${topic}\n\nProduce title, full_script, and scenes with distinct visual_prompt per scene.`,
    },
  ],
  response_format: {
    type: 'json_schema',
    json_schema: {
      name: 'script_and_scenes',
      strict: true,
      schema: SCHEMA,
    },
  },
};

return [{ json: { openaiBody } }];
