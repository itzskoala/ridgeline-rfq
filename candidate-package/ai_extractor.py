#ai_extractor.py

'''
system prompt, API call injests markdown + system prompt + assisant prompt

we are asking to return what is the README / json output which is...

checkformat.py + 

  "E003": {
      "classification": "rfq",
      "revises": null,
      "duplicate_of": null,
      "needs_review": false,
      "line_items": [
        {
          "id": "E003-1",
          "raw": "1) 20 jts - 2\"",
          "qty": 20,
          "qty_tol": 0,
          "uom": "EA",
          "source": "body",
          "must_mention": [
            "pipe",
            "sch 40|schedule 40",
            "a53b",
            "erw",
            "t&c|threaded and coupled|thd and cpld|t/c"
          ],
          "must_not_mention": [
            "malleable",
            "150#"
          ],
          "sku": "RL-41907",
          "match": "matched",
          "candidates": []
        },
        {
          "id": "E003-2",
          "raw": "2) 10 jts - 3\"",
          "qty": 10,
          "qty_tol": 0,
          "uom": "EA",
          "source": "body",
          "must_mention": [
            "pipe",
            "sch 40|schedule 40",
            "a53b",
            "erw",
            "t&c|threaded and coupled|thd and cpld|t/c"
          ],
          "must_not_mention": [
            "malleable",
            "150#"
          ],
          "sku": "RL-14934",
          "match": "matched",
          "candidates": []
        },
        {

so we need to put AI OUTPUT in a pydantic first  + validate / ensure fields are correct/acucray then .to_json

to create parsed.json!!!!!

steps after that are to just test with answer key, create syntheitc data, clean files, maybe do the optional time permitting, test with other LLMs...



Instructions to give to the LLM?




'''

