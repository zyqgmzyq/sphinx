import os
import glob

theme = 'my_theme'

index = '_index.rst'

listdir = [file for file in os.listdir(os.path.join('.')) if os.path.isdir(file)]
listdir.remove(theme)

file_dict = {}

rst_files = []

for element in listdir:
    files = sorted(glob.glob(os.path.join('.', element, '*.md')))
    file_dict[element] = files

# 写子索引
for file_dir in file_dict:
    index_file_name = file_dir + index
    rst_file = os.path.join('.', file_dir, index_file_name)
    rst_files.append(rst_file)
    with open(rst_file, 'w', encoding='utf-8') as g:
        g.write('.. yaqin-note documentation master file, created by\n'
                '   sphinx-quickstart on Sun Jun 21 20:24:32 2020.\n'
                '   You can adapt this file completely to your liking, but it should at least\n'
                '   contain the root `toctree` directive.\n'
                '\n')
        g.write(str(file_dir).capitalize() + '\n')
        g.write('======================================\n')
        g.write('\n')
        g.write('.. toctree::\n'
                '   :maxdepth: 2\n'
                '\n')
        files = file_dict[file_dir]
        for file in files:
            g.write('   ' + os.path.split(file)[-1] + '\n')

# 写根索引
with open(os.path.join('.', 'index.rst'), 'w', encoding='utf8') as g:
    g.write('.. yaqin-note documentation master file, created by\n'
            '   sphinx-quickstart on Sun Jun 21 20:24:32 2020.\n'
            '   You can adapt this file completely to your liking, but it should at least\n'
            '   contain the root `toctree` directive.\n'
            '\n'
            'Note\n'
            '======================================\n'
            '\n'
            '.. toctree::\n'
            '   :maxdepth: 2\n'
            '\n')
    for rst_f in rst_files:
        path_split = os.path.split(rst_f)

        g.write('   /{}/{}\n'.format(os.path.split(path_split[-2])[-1], path_split[-1]))
