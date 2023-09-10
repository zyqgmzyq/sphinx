# vimrc配置

```shell
set path=./**,**,
"set colorcolumn=80
nmap csm :set colorcolumn=75<CR> 
nmap csmn :set colorcolumn=<CR> 
set hls
"set tabstop=4
"set softtabstop=4
"set shiftwidth=4
"set expandtab
"set autoindent
highlight OverLength ctermbg=yellow ctermfg=black guibg=#592929
match OverLength /\%81v.\+/

set cscopequickfix=s-,c-,d-,i-,t-,e-,g-
nmap wm :WMToggle<cr>
map  wmb :BottomExplorerWindow<cr>
map wmt  :FirstExplorerWindow<cr>
set nocst
set noswapfile
nmap css :cs find s <C-R>=expand("<cword>")<CR><CR>
nmap csg :cs find g <C-R>=expand("<cword>")<CR><CR>
nmap csc :cs find c <C-R>=expand("<cword>")<CR><CR>
nmap cst :cs find t <C-R>=expand("<cword>")<CR><CR>
nmap cse :cs find e <C-R>=expand("<cword>")<CR><CR>
"Leaderf settings
nnoremap <leader>f :LeaderfFile<CR>
nnoremap <silent> <leader>m :LeaderfMru<CR>
nnoremap <silent> <leader>b :LeaderfBuffer<CR>
nnoremap <silent> <leader>o :LeaderfFunction<CR>
nnoremap <silent> <leader>h :Leaderf cmdHistory<CR>
nnoremap <silent> <leader>rg :Leaderf rg <CR>
nnoremap <leader>r yiw:%s/\<<C-r>"\>//gc<left><left><left>
nnoremap <silent> <leader>y "+y <CR>
nnoremap <silent> <leader>p "+p <CR>
"nnoremap <leader>r :%s/\<<C-r><C-w>\>//g<left><left>
"let g:Lf_ReverseOrder = 1
let g:Lf_PreviewInPopup = 1
let g:Lf_WildIgnore = {
            \ 'dir': ['.svn','.git','.hg'],
            \ 'file': ['*.sw?','~$*','*.patch','*.bak','*.exe','*.o','*.so','*.py[co]','cscope.*', 'tag*.*']
            \}
let g:Lf_RgConfig = [
        \ '--glob=!.git',
        \ '--glob=!.metadata',
        \ '--glob=!cscope.*',
        \ '--glob=!filenametags',
        \ '--glob=!tags',
        \ '--glob=!tagfiles',
        \ '--glob=!namelist',
        \ '--glob=!*.pl',
        \ '--hidden'
        \ ]

"nmap csf :cs find f <C-R>=expand("<cfile>")<CR><CR>
"nmap csi :cs find i <C-R>=expand("<cfile>")<CR><CR>
"nmap csd :cs find d <C-R>=expand("<cword>")<CR><CR>

"nmap csv :cs find g 
nmap csq :q<CR> 
nmap csql <C-W>l:q<CR> 
nmap csqh <C-W>h:q<CR> 
nmap wwl 30<C-W>> 
nmap wws 30<C-W>< 
nmap csh :sp<CR> 
nmap csu :vs<CR> 
nmap csi :exe Adammax()<CR> 
nmap csf :exe Adammaxh()<CR> 
nmap csb :Gblame<CR>o<C-W>j:q<CR><C-W>kcsi 
nmap q :q<CR>
" Using 'CTRL-spacebar' then a search type makes the vim window
" split horizontally, with search result displayed in
" the new window.

nmap <C-s>s :scs find s <C-R>=expand("<cword>")<CR><CR>
nmap <C-s>g :scs find g <C-R>=expand("<cword>")<CR><CR>
nmap <C-s>c :scs find c <C-R>=expand("<cword>")<CR><CR>
nmap <C-s>t :scs find t <C-R>=expand("<cword>")<CR><CR>
nmap <C-s>e :scs find e <C-R>=expand("<cword>")<CR><CR>
nmap <C-s>f :scs find f <C-R>=expand("<cfile>")<CR><CR>
nmap <C-s>i :scs find i <C-R>=expand("<cfile>")<CR><CR>
nmap <C-s>d :scs find d <C-R>=expand("<cword>")<CR><CR>

highlight MyGroup ctermbg=gray guibg=gray

highlight MyGroup2 ctermbg=6 guibg=yellow
highlight MyGroup3 ctermbg=2 guibg=gray
nmap maf :match  MyGroup /<C-R>=expand("<cword>")<CR>/<CR>
nmap mas :2match  MyGroup2 /<C-R>=expand("<cword>")<CR>/<CR>
nmap mat :3match  MyGroup3 /<C-R>=expand("<cword>")<CR>/<CR>
nmap man :match<CR> :2match<CR> :3match<CR>
nmap <C-l> 10l
nmap <C-h> 10h
nmap <C-j> 10j
nmap <C-k> 10k

"if ! has("gui_running")
"  set t_Co=256
"endif
"if &diff
"    colors peaksea
"endif
colors peaksea
set mouse=a
nmap <C-e> $
nmap <C-a> ^
nmap <C-u> [[o#if 0<Esc>][O#endif nmap  [[jdd][kdd<Esc> 
nmap <C-u>m  <Esc>:r !date<CR>i/*Adam Tao@cisco edited at <Esc>$a*/<Esc> 
"nmap <Tab> i<Space><Space><Space><Space><Esc>
nnoremap <silent>  tlt :TlistToggle<CR>
nnoremap <silent>  tlu :TlistUpdate<CR>
nnoremap <silent> cwn :cn<CR>
nnoremap <silent> col :col<CR>
nnoremap <silent> cne :cnew<CR>
nnoremap <silent> cwp :cp<CR>
nnoremap <silent> cwc :ccl<CR>
nnoremap <silent> cwo :cw<CR>
"Add for the fuzzer finder
"nmap uff :FufFile **/<C-R>=expand("<cword>")<CR><CR>
"nmap fff :FufFile **/<CR>
nmap fff :LookupFile<CR>
"nmap ffd :FufFileWithCurrentBufferDir<CR>
nmap ffb :FufBuffer<CR>
nmap ffc iprintf("enter the debug for adam %s %d\n", __FUNCTION__, __LINE__);
nmap fft :FufTag<CR>
highlight Pmenu ctermbg=white ctermfg=black
highlight PmenuSel ctermbg=yellow ctermfg=black
highlight Search  ctermbg=white ctermfg=black cterm=bold
nmap grepw :vimgrep /<C-R>=expand("<cword>")<CR>/j 
nmap grepo :vimgrep /<C-R>=expand("<cword>")<CR>/j <C-R>=expand("%")<CR>
nmap grepd :vimgrep /<C-R>=expand("<cword>")<CR>/j <C-R>=expand("%:h")<CR>/**/* 
nmap grepl :!ogrep normal  <C-R>=expand("<cword>")<CR>
nmap ccw :!pandoc <C-R>=expand("%")<CR>\|w3m<CR>
"nmap wwt :let g:winManagerWindowLayout = 'TagList'
"nmap wwf :let g:winManagerWindowLayout e 'FileExplorer'
let g:winManagerWindowLayout = "BufExplorer,FileExplorer|TagList"
let g:winManagerWidth = 30
let g:AutoOpenWinManager = 1
"let Tlist_Auto_Open=1
"let Tlist_Use_Right_Window=1
let Tlist_Exit_OnlyWindow=1
"nmap <C-r>  <C-w>=
nmap hex  :%!xxd<CR>
nmap hexr :%!xxd -r<CR>
nmap pl :Explore<CR>
 nmap ww :w<CR>
 nmap wwq :wq<CR>
"NERD tree related
nmap pn :NERDTreeToggle <C-R>=expand("%:h")<CR><CR>
nmap pc :cd <C-R>=expand("%:h")<CR><CR>
:let g:NERDTreeDirArrows=0
:let g:LookupFile_TagExpr='"./filenametags"'
:let g:LookupFile_ignorecase=1
set ignorecase
nmap gn :set ignorecase 
nmap zgn :set noignorecase 
nmap vs :vs<CR>:Explore<CR> 
let g:Powerline_symbols = 'fancy'
"let g:Powerline_symbols = 'unicode'
"let g:Powerline_colorscheme = 'solarized'
"let g:Powerline_theme = 'solarized16'
"let g:Powerline_theme = 'default'
"let g:Powerline_colorscheme = 'skwp'
set nocompatible
set noincsearch
set ignorecase
"set laststatus=2
set encoding=utf-8
set t_Co=256
"nmap qq :q<CR>
"nmap du <C-w>k
"nmap dd <C-w>u
set ww=b,s,h,l
set nu

" abbreviates 
abbreviate ACKme Acked-by: Zhe Tao <zhe.tao@intel.com>
abbreviate JING jingjing.wu@intel.com 
abbreviate HELIN helin.zhang@intel.com 
abbreviate __S <tab>--yliu
abbreviate dpdkorg dev@dpdk.org 
"abbreviate DPDK 'NPG-PRC-SW DPDK <npg-prc-sw.dpdk@intel.com>'


if has("cscope") && filereadable("/usr/bin/cscope")
   set csprg=/usr/bin/cscope
   set csto=0
   set cst
   set nocsverb
   " add any database in current directory
   if filereadable("cscope.out")
      cs add cscope.out
   " else add database pointed to by environment
   elseif $CSCOPE_DB != ""
      cs add $CSCOPE_DB
   endif
   set csverb
endif
nmap <C-Right> <C-w><Right><CR> 
nmap <C-Left> <C-w><Left><CR> 
nmap <C-Up> <C-w><Up><CR> 
nmap <C-Down> <C-w><Down><CR> 
set fileencodings=utf-8,gb2312,gb18030,gbk,ucs-bom,cp936,latin1
"set langmenu=zh_CN.UTF-8
"language messages zh_CN.UTF-8
set termencoding=utf-8
set encoding=utf-8
set mouse=v
call plug#begin('~/.vim/plugged')
    " Shorthand notation for plugin
    Plug 'Yggdroot/LeaderF', { 'do': ':LeaderfInstallCExtension' }
    Plug 'lfv89/vim-interestingwords'
    Plug 'jiangmiao/auto-pairs'
    Plug 'vim-airline/vim-airline'
    Plug 'vim-airline/vim-airline-themes'
call plug#end()
colorscheme desert
syntax on
set showmatch
nnoremap <silent> <leader>k :call InterestingWords('n')<cr>
vnoremap <silent> <leader>k :call InterestingWords('v')<cr>
nnoremap <silent> <leader>K :call UncolorAllWords()<cr>
nnoremap <silent> n :call WordNavigation(1)<cr>
nnoremap <silent> N :call WordNavigation(0)<cr>
set nocompatible
filetype off
set rtp+=~/.vim/bundle/Vundle.vim
call vundle#begin()
Plugin 'VundleVim/Vundle.vim'
Plugin 'Valloric/YouCompleteMe'
Plugin 'zivyangll/git-blame.vim'
call vundle#end()
filetype plugin indent on
let g:ycm_complete_in_comments = 1
let g:ycm_complete_in_strings = 1
let g:ycm_global_ycm_extra_conf='~/.vim/.ycm_extra_conf.py'
let g:ycm_show_diagnostics_ui = 0
let g:ycm_key_list_stop_completion = ['<CR>']
set backspace=indent,eol,start
highlight PMenu ctermfg=0 ctermbg=grey guifg=black guibg=darkgrey
highlight PMenuSel ctermfg=242 ctermbg=darkgrey guifg=darkgrey guibg=black
let g:ycm_filetype_whitelist = {
			\ "c":1,
			\ "cpp":1,
			\ "objc":1,
			\ "sh":1,
			\ "zsh":1,
			\ "zimbu":1,
			\ }
"inoremap <expr> <CR> pumvisible() ? "\<C-y>" : "\<CR>" |
"set cursorline
nmap <leader>c :set cursorline<CR>:set cursorcolumn<CR>
nmap <leader>C :set nocursorline<CR>:set nocursorcolumn<CR>
hi CursorLine   cterm=NONE ctermbg=white ctermfg=darkred guibg=darkred guifg=white
hi CursorColumn cterm=NONE ctermbg=darkred ctermfg=white guibg=darkred guifg=white
hi Cursor cterm=NONE ctermbg=white ctermfg=darkred guibg=darkred guifg=white
hi CursorIM cterm=NONE ctermbg=darkred ctermfg=white guibg=darkred guifg=white
cnoremap <c-a> <C-B>
hi CursorLine   cterm=NONE ctermbg=darkgreen ctermfg=white guibg=darkblue guifg=white
hi CursorColumn cterm=NONE ctermbg=darkgrey ctermfg=white guibg=darkgreen guifg=white
set colorcolumn=120
let g:airline#extensions#tabline#enabled = 1
nnoremap <C-b> :bp <cr>
nnoremap <C-n> :bn <cr>
nmap csp csu<C-w>lcsg <leader>c
nmap csi csu<C-w>lcsc <leader>c
```

