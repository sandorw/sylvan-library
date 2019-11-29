import argparse
import json
import os
import requests
from os import path

def load_card_data(is_offline):
    '''Sets up card dictionary'''
    cards = {}
    card_data = read_card_data(is_offline)
    if not card_data:
        raise RuntimeError('No card data available')
    for card in card_data:
        card_name = card['name'].split(' //')[0]
        cards[card_name] = card
    return cards

def read_card_data(is_offline):
    '''Loads card data from cache or Scryfall'''
    if path.exists('card-data.json'):
        with open('card-data.json') as json_file:
            data = json.load(json_file)
            if is_offline:
                return data['data']
            resp = requests.head('https://archive.scryfall.com/json/scryfall-default-cards.json')
            if resp.headers['etag'] == data['etag']:
                print('Cached data valid')
                return data['data']
    return refresh_card_data()

def refresh_card_data():
    '''Fetches card data from Scryfall and saves it to disk'''
    print('Fetching card data...')
    resp = requests.get('https://archive.scryfall.com/json/scryfall-default-cards.json')
    cache_data = {}
    cache_data['etag'] = resp.headers['etag']
    cache_data['data'] = resp.json()
    with open('card-data.json', 'w') as outfile:
        json.dump(cache_data, outfile)
    return cache_data['data']

def read_decklists(dirs):
    '''Loads all decklists in a given directory'''
    decks = {}
    for dir in dirs:
        for infile in os.listdir(dir):
            if infile[-4:] != '.txt':
                continue
            filename = dir + '/' + infile
            try:
                deck = load_deck(filename)
                deck_id = deck['deck_id']
                decks[deck_id] = deck

            except:
                print('File {} could not be analyzed.'.format(filename))
                continue
    return decks

def load_deck(infile):
    '''Loads a single decklist'''
    with open(infile) as deck_file:
        lines = [line.strip('\n') for line in deck_file.readlines()]
        num_lines = len(lines)
        deck_id = lines[0].split(':')[1].strip(' ')
        player_id = lines[1].split(':')[1].strip(' ')
        date = lines[2].split(':')[1].strip(' ')
        colors = lines[3].split(':')[1].strip(' ')
        labels = lines[4].split(':')[1].split(',')
        labels = [x.strip(' ') for x in labels]
        match_record = lines[5].split(':')[1].strip(' ').split('-')
        match_wins = match_record[0]
        match_losses = match_record[1]
        match_draws = 0
        if len(match_record) == 3:
            match_draws = match_record[2]
        game_record = lines[6].split(':')[1].strip(' ').split('-')
        game_wins = game_record[0]
        game_losses = game_record[1]
        game_draws = 0
        if len(game_record) == 3:
            game_draws = game_record[2]
        index = 7
        games = {}
        while lines[index] != '':
            game_data = lines[index].split(':')
            opponent = int(game_data[0].split('.')[1].strip(' '))
            record = game_data[1].strip(' ').split('-')
            wins = record[0]
            losses = record[1]
            draws = 0
            if len(record) == 3:
                draws = record[2]
            games[opponent] = {'wins': int(wins), 'losses': int(losses), 'draws': int(draws)}
            index += 1
        index += 1
        maindeck = []
        sideboard = []

        while index < num_lines and lines[index] != '':
            num, card_name = lines[index].split(' ', 1)
            maindeck.extend([card_name]*int(num))
            index += 1
        index += 1
        while index < num_lines and lines[index] != '':
            num, card_name = lines[index].split(' ', 1)
            sideboard.extend([card_name]*int(num))
            index += 1
        
        deck = {
            'deck_id': int(deck_id),
            'player_id': int(player_id),
            'date': date,
            'colors': colors,
            'labels': labels,
            'match_record': {'wins': int(match_wins), 'losses': int(match_losses), 'draws': int(match_draws)},
            'game_record': {'wins': int(game_wins), 'losses': int(game_losses), 'draws': int(game_draws)},
            'game_results': games,
            'maindeck': maindeck,
            'sideboard': sideboard}
        return deck

def validate_decklists(decks, cards):
    for deck in decks.values():
        deck_id = deck['deck_id']
        if len(deck['maindeck']) < 40:
            print('maindeck for deck {} missing cards'.format(deck_id))
        for card in deck['maindeck'] + deck['sideboard']:
            if card not in cards.keys():
                print('misspelled or missing card: {}'.format(card))
        for opponent in deck['game_results'].keys():
            if opponent not in decks:
                print('missing deck_id: {}'.format(opponent))

# Can I write a generalized version of the analysis and cover the things I want?
# Would allow for count statistics as well as win rate analysis
#   card winrate: win rate grouped by maindeck
#   player winrate: win rate grouped by player ID
#   player count by archetype: count grouped by playerID and archetype - probably want to divide by total count
#   

def analyze_results(card_data, decks, deck_predicate):
    archetypes = {}
    players = {}
    cards = {}
    for deck in decks.values():
        if not deck_predicate(deck):
            continue
        player_id = deck['player_id']
        if player_id not in players.keys():
            players[player_id] = {'overall_record':{'wins':0, 'losses':0, 'draws':0}, 'player_matchups':{}, 'archetype_record':{}}
        accumulate_results(players[player_id]['overall_record'], deck['game_record'])
        for archetype in deck['labels']:
            if archetype not in archetypes.keys():
                archetypes[archetype] = {'overall_record':{'wins':0, 'losses':0, 'draws':0}, 'matchups':{}}
            if archetype not in players[player_id]['archetype_record'].keys():
                players[player_id]['archetype_record'][archetype] = {'wins':0, 'losses':0, 'draws':0}
            accumulate_results(archetypes[archetype]['overall_record'], deck['game_record'])
            accumulate_results(players[player_id]['archetype_record'][archetype], deck['game_record'])
        for card in deck['maindeck']:
            if card in ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest']:
                continue
            if card not in cards.keys():
                cards[card] = {'overall_record':{'wins':0, 'losses':0, 'draws':0}, 'maindeck':0, 'sideboard':0}
            accumulate_results(cards[card]['overall_record'], deck['game_record'])
            cards[card]['maindeck'] += 1
        for card in deck['sideboard']:
            if card not in cards.keys():
                cards[card] = {'overall_record':{'wins':0, 'losses':0, 'draws':0}, 'maindeck':0, 'sideboard':0}
            cards[card]['sideboard'] += 1

    for tuple in archetypes.items():
        archetype = tuple[0]
        winrate_results = tuple[1]['overall_record']
        winrate_results['winrate'] = get_winrate(winrate_results) 
        matchup_results = tuple[1]['matchups']
    for tuple in players.items():
        player_id = tuple[0]
        player_results = tuple[1]
        player_results['overall_record']['winrate'] = get_winrate(player_results['overall_record'])
        for opposing_player in player_results['player_matchups'].keys():
            player_result = player_results['player_matchups'][opposing_player]
            player_result['winrate'] = get_winrate(player_result)
        for archetype in player_results['archetype_record'].keys():
            archetype_result = player_results['archetype_record'][archetype]
            archetype_result['winrate'] = get_winrate(archetype_result)
    for card in cards.values():
        card['overall_record']['winrate'] = get_winrate(card['overall_record'])
        card['maindeck_rate'] = float(card['maindeck']) / (card['maindeck'] + card['sideboard'])

def get_winrate(record):
    return float(record['wins']) / (record['wins'] + record['losses'] + record['draws'])

def accumulate_results(record, results):
    record['wins'] += results['wins']
    record['losses'] += results['losses']
    record['draws'] += results['draws']

def card_archetypes(decks):
    cards = {}
    counts = {}
    for deck in decks.values():
        for card in deck['maindeck']:
            if card in ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest']:
                continue
            if card not in cards.keys():
                cards[card] = {}
                counts[card] = 0
            counts[card] += 1
            for archetype in deck['labels']:
                if archetype not in cards[card].keys():
                    cards[card][archetype] = 0
                cards[card][archetype] += 1
    print('')
    print('Card archetypes')
    for card in cards.keys():
        results = cards[card]
        for archetype in results.keys():
            results[archetype] = float(results[archetype]) / counts[card]
        print('{}: {}'.format(card, sorted(results.items(), key=lambda kv:kv[1], reverse=True)))

def archetype_matchups(decks):
    archetypes = {}
    for deck in decks.values():
        for archetype in deck['labels']:
            if archetype not in archetypes:
                archetypes[archetype] = {}
            for entry in deck['game_results'].items():
                opposing_deck = decks[entry[0]]
                record = entry[1]
                for opposing_archetype in opposing_deck['labels']:
                    if opposing_archetype not in archetypes[archetype]:
                        archetypes[archetype][opposing_archetype] = {'wins':0, 'losses':0, 'draws':0}
                    archetypes[archetype][opposing_archetype]['wins'] += record['wins']
                    archetypes[archetype][opposing_archetype]['losses'] += record['losses']
                    archetypes[archetype][opposing_archetype]['draws'] += record['draws']
    print('')
    print('Archetype matchups')
    for entry in archetypes.items():
        archetype = entry[0]
        archetype_matchup_results = entry[1]
        for opposing_entry in archetype_matchup_results.items():
            opposing_archetype = opposing_entry[0]
            record = opposing_entry[1]
            total = record['wins'] + record['losses'] + record['draws']
            win_rate = float(record['wins']) / total
            print('{} vs {}: winrate {}, {}-{}-{}'.format(archetype, opposing_archetype, win_rate, record['wins'], record['losses'], record['draws']))

def main():
    parser = argparse.ArgumentParser(description='Analyzes cube decklists')
    parser.add_argument('--offline', action='store_true', help='Use local cached card data')
    parser.add_argument('-d', '--dir', action='append', help='Directory to read draft results from')
    parser.add_argument('--filter-list', help='List of cards to filter the results down to')
    parser.add_argument('-p', '--player', action='append', help='Filter results to decks played by a certain player ID')
    parser.add_argument('-a', '--archetype', action='append', help='Filter results to decks of a certain archetype')
    args = parser.parse_args()

    deck_predicate = lambda deck: True
    if args.player:
        deck_predicate = lambda deck: deck_predicate(deck) and deck['player_id'] in args.player
    if args.archetype:
        deck_predicate = lambda deck: deck_predicate(deck) and (set(args.archetype) & set(deck['labels']))

    card_data = load_card_data(args.offline)
    decks = read_decklists(args.dir)
    validate_decklists(decks, card_data)

    analyze_results(card_data, decks, deck_predicate)

    archetype_analysis(decks) # winrate grouped by archetype 
    player_analysis(decks) # winrate grouped by player id
    card_winrates(decks) # winrate grouped by maindeck (filter out basics)
    maindeck_rates(decks) # ??
    card_archetypes(decks) # count grouped by card and label
    archetype_matchups(decks) # winrate grouped by archetype and opposing archetype

    # unclear how to filter out basics when handling the maindeck
    # unclear how to group by sub-attributes of opposing decks except by some special logic
    # unclear how to generalize maindeck rate

if __name__ == '__main__':
    main()
