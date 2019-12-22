import argparse
import readline
from os import path

cards = []

def load_list():
    list_file = "list.txt"
    with open(list_file) as file:
        lines = [line.strip('\n') for line in file.readlines()]
        num_lines = len(lines)
        index = 0
        while index < num_lines and lines[index] != '':
            cards.append(lines[index])
            index += 1 

def completer(text, state):
    options = [i for i in cards if i.startswith(text)]
    if state < len(options):
        return options[state]
    else:
        return None

def read_decklists():
    print "Enter first deckId"
    first_deck_id = int(raw_input("> "))
    current_deck_id = first_deck_id - 1    
    print "Enter date (YYYY-MM-DD)"
    date = raw_input("> ")

    input = ""
    while True:
        current_deck_id += 1
        print('Current deck id: {}'.format(current_deck_id))
        print "Enter playerId"
        player_id = raw_input("> ")
        print "Enter colors (e.g. BRg)"
        colors = raw_input("> ")
        print "Enter labels"
        labels = raw_input("> ")

        filename = str(current_deck_id) + '_' + colors + '.txt'
        with open(filename, 'w') as file:
            file.write('DeckId: ' + str(current_deck_id) + '\n')
            file.write('Pilot: ' + player_id + '\n')
            file.write('Date: ' + date + '\n')
            file.write('Colors: ' + colors + '\n')
            file.write('Labels: ' + labels + '\n')
            file.write('Match Record: \n')
            file.write('Game Record: \n')
            file.write('vs. :\n')
            file.write('\n')

            print "Enter maindeck cards, 'sideboard' to move on"
            while True:
                input = raw_input("> ")
                if input == 'sideboard':
                    break
                if input[0].isdigit():
                    file.write(input + '\n')
                else:
                    file.write('1 ' + input + '\n')
            file.write('\n')

            print "Enter sideboard cards, 'next' to move to next decklist, 'end' to exit"
            while True:
                input = raw_input("> ")
                if input == 'next' or input == 'end':
                    break
                file.write('1 ' + input + '\n')
        if input == 'end':
            break

def main():
    load_list()

    readline.parse_and_bind("tab: complete")
    readline.set_completer_delims("\t\n\"\\'`@$><=;|&{(")
    readline.set_completer(completer)

    read_decklists()

if __name__ == '__main__':
    main()

