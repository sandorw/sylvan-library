import json
import os
import requests
from os import path

def load_card_data(is_offline):
    '''Sets up card dictionary'''
    cards = {}
    card_data = read_card_data(is_offline)
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

def read_decklists(directory):
    '''Loads all decklists in a given directory'''
    decks = {}
    for infile in os.listdir(directory):
        if infile[-4:] != '.txt':
            continue
        filename = directory + '/' + infile
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

def archetype_analysis(decks):
    archetypes = {}
    for deck in decks.values():
        for archetype in deck['labels']:
            if archetype not in archetypes.keys():
                archetypes[archetype] = {'wins':0, 'losses':0, 'draws':0}
            archetypes[archetype]['wins'] += deck['game_record']['wins']
            archetypes[archetype]['losses'] += deck['game_record']['losses']
            archetypes[archetype]['draws'] += deck['game_record']['draws']
    for archetype in archetypes.keys():
        results = archetypes[archetype]
        win_rate = float(results['wins']) / (results['wins'] + results['losses'] + results['draws'])
        archetypes[archetype]['win_rate'] = win_rate
    print('')
    print('Archetype win rates')
    for archetype_tuple in sorted(archetypes.items(), key=lambda kv: kv[1]['win_rate'], reverse=True):
        archetype = archetype_tuple[0]
        results = archetype_tuple[1]
        print('Archetype {}: win rate {}, {}-{}-{}'.format(archetype, results['win_rate'], results['wins'], results['losses'], results['draws']))

def player_analysis(decks):
    players = {}
    for deck in decks.values():
        player_id = deck['player_id']
        if player_id not in players.keys():
            players[player_id] = {'wins':0, 'losses':0, 'draws':0}
        players[player_id]['wins'] += deck['game_record']['wins']
        players[player_id]['losses'] += deck['game_record']['losses']
        players[player_id]['draws'] += deck['game_record']['draws']
    print('')
    print('Player win rates')
    for player in sorted(players.keys()):
        results = players[player]
        win_rate = float(results['wins']) / (results['wins'] + results['losses'] + results['draws'])
        print('Player {}: win rate {}, {}-{}-{}'.format(player, win_rate, results['wins'], results['losses'], results['draws']))

def card_winrates(decks):
    cards = {}
    for deck in decks.values():
        for card in deck['maindeck']:
            if card in ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest']:
                continue
            if card not in cards.keys():
                cards[card] = {'wins':0, 'losses':0, 'draws':0}
            cards[card]['wins'] += deck['game_record']['wins']
            cards[card]['losses'] += deck['game_record']['losses']
            cards[card]['draws'] += deck['game_record']['draws']
    for card in cards.keys():
        results = cards[card]
        win_rate = float(results['wins']) / (results['wins'] + results['losses'] + results['draws'])
        cards[card]['win_rate'] = win_rate
    print('')
    print('Card win rates')
    for card_tuple in sorted(cards.items(), key=lambda kv: kv[1]['win_rate'], reverse=True):
        card_name = card_tuple[0]
        card_results = card_tuple[1]
        print('{}: win rate {}, {}-{}-{}'.format(card_name, card_results['win_rate'], card_results['wins'], card_results['losses'], card_results['draws']))

def maindeck_rates(decks):
    cards = {}
    for deck in decks.values():
        for card in deck['maindeck']:
            if card in ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest']:
                continue
            if card not in cards.keys():
                cards[card] = {'maindeck':0, 'sideboard':0}
            cards[card]['maindeck'] += 1
        for card in deck['sideboard']:
            if card not in cards.keys():
                cards[card] = {'maindeck':0, 'sideboard':0}
            cards[card]['sideboard'] += 1
    for card in cards.keys():
        results = cards[card]
        maindeck_rate = float(results['maindeck']) / (results['maindeck'] + results['sideboard'])
        cards[card]['maindeck_rate'] = maindeck_rate
    print('')
    print('Card maindeck rates')
    for card_tuple in sorted(cards.items(), key=lambda kv: kv[1]['maindeck_rate'], reverse=True):
        card_name = card_tuple[0]
        card_results = card_tuple[1]
        print('{}: maindeck rate {}, {}-{}'.format(card_name, card_results['maindeck_rate'], card_results['maindeck'], card_results['sideboard']))

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

def main():
    card_data = load_card_data(True)
    decks = read_decklists('draft-results')
    validate_decklists(decks, card_data)
    archetype_analysis(decks)
    player_analysis(decks)
    card_winrates(decks)
    maindeck_rates(decks)
    card_archetypes(decks)

if __name__ == '__main__':
    main()
