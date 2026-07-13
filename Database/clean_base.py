import os

base_path = os.path.join(os.path.dirname(__file__), 'base.txt')
clean_path = os.path.join(os.path.dirname(__file__), 'clean_base.txt')

with open(base_path, 'r', encoding='utf-8') as infile, open(clean_path, 'w', encoding='utf-8') as outfile:
    joke_lines = []
    for line in infile:
        line = line.strip().replace('\t', '')
        if not line:
            if joke_lines:
                outfile.write('\n'.join(joke_lines) + '\n\n')
                joke_lines = []
                
            continue
        joke_lines.append(line)
        
    # Write the last joke if any
    if joke_lines:
        outfile.write('\n'.join(joke_lines) + '\n\n')