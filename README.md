# sylvan-library

Historical decklists and match results from my cube.

## Analysis

Run `analysis.py` to analyze the results. Some examples are below:

`python3 analysis.py -d draft-results --winrate labels` loads the decklists from the `draft-results/` dir and aggregates game winrates by deck label, e.g. indicating that decks with the `Stax` label have a 45.7% winrate. Aggregations can be combined; for example, `python3 analysis.py -d draft-results --winrate player_id labels` breaks down the winrate of decks with a given label for each player individually. 

`python3 analysis.py -d draft-results --count player_id` aggregates instead a count or fraction, in this case giving the total number of drafts that each player has participated in. 

Available deck attributes for aggregation:
- deck_id
- player_id
- date
- colors 
- labels
- match_record
- game_record
- maindeck
- sideboard

These attributes can also be prepended with `opposing_`, which will aggregate results based on attributes of opposing decklists. `python3 analysis.py -d draft-results -l list.txt --winrate labels opposing_labels`, for example, will display the  winrate of each label against each opposing deck label. 

There are several filters you can apply to decks before they are included in the results:
- `-p` filters results to those with provided player IDs
- `-a` filters results to those with the provided label(s)

`python3 analysis.py -d draft-results -l list.txt --maindeckRate` displays the maindeck rate for cards in the cube, and the `-l list.txt` flag filters the results to those in the provided file (in this case, to cards currently in the cube).
