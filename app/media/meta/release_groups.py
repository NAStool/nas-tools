import re

#  官组
rg_0ff = ['FF(?:(?:A|WE)B|CD|E(?:DU|B)|TV)']
rg_1pt = []
rg_52pt = []
rg_audiences = ['Audies', 'AD(?:Audio|E(?:|book)|Music|Web)']
rg_azusa = []
rg_beitai = ['BeiTai']
rg_btschool = ['Bts(?:CHOOL|HD|PAD|TV)', 'Zone']
rg_carpt = ['CarPT']
rg_chdbits = ['CHD(?:|Bits|PAD|(?:|HK)TV|WEB)', 'StBOX', 'OneHD', 'Lee', 'xiaopie']
rg_discfan = []
rg_dragonhd = []
rg_eastgame = ['(?:(?:iNT|(?:HALFC|Mini(?:S|H|FH)D))-|)TLF']
rg_filelist = []
rg_gainbound = ['(?:DG|GBWE)B']
rg_hares = ['Hares(?:|(?:M|T)V|Web)']
rg_hd4fans = []
rg_hdarea = ['HDA(?:pad|rea|TV)', 'EPiC']
rg_hdatmos = []
rg_hdbd = []
rg_hdchina = ['HDC(?:|hina|TV)', 'k9611', 'tudou', 'iHD']
rg_hddolby = ['D(?:ream|BTV)', '(?:HD|QHstudI)o']
rg_hdfans = ['beAst(?:|TV)']
rg_hdhome = ['HDH(?:|ome|Pad|TV|WEB)']
rg_hdpt = ['HDPT(?:|Web)']
rg_hdsky = ['HDS(?:|ky|TV|Pad|WEB)', 'AQLJ']
rg_hdtime = []
rg_HDU = []
rg_hdvideo = []
rg_hdzone = ['HDZ(?:|one)']
rg_hhanclub = ['HHWEB']
rg_hitpt = []
rg_htpt = ['HTPT']
rg_iptorrents = []
rg_joyhd = []
rg_keepfrds = ['FRDS', 'Yumi', 'cXcY']
rg_lemonhd = ['L(?:eague(?:(?:C|H)D|(?:M|T)V|NF)|WEB)', 'i18n', 'CiNT']
rg_mteam = ['MTeam(?:|TV)', 'MPAD']
rg_nanyangpt = []
rg_nicept = []
rg_oshen = []
rg_ourbits = ['Our(?:Bits|TV)', 'FLTTH', 'Ao', 'PbK', 'MGs', 'iLove(?:HD|TV)']
rg_piggo = ['PiGo(?:NF|(?:H|WE)B)']
rg_ptchina = []
rg_pterclub = ['PTer(?:|DIY|Game|(?:M|T)V|WEB)']
rg_pthome = ['PTH(?:|Audio|eBook|music|ome|tv|WEB)']
rg_ptmsg = []
rg_ptsbao = ['PTsbao', 'OPS', 'F(?:Fans(?:AIeNcE|BD|D(?:VD|IY)|TV|WEB)|HDMv)', 'SGXT']
rg_pttime = []
rg_putao = ['PuTao']
rg_soulvoice = []
rg_springsunday = ['CMCT(?:|V)']
rg_tccf = []
rg_tjupt = ['TJUPT']
rg_totheglory = ['TTG', 'WiKi', 'NGB', 'DoA', '(?:ARi|ExRE)N']
rg_U2 = []
rg_ultrahd = []

#  其他常见组
rg_other = ['B(?:MDru|eyondHD|TN)', 'C(?:fandora|trlhd|MRG)', 'DON', 'EVO', 'FLUX', 'HONE(?:|yG)', 'N(?:oGroup|T(?:b|G))', 'PandaMoon', 'SMURF', 'T(?:EPES|aengoo|rollHD )']
rg_anime = ['ANi', 'HYSUB', 'KTXP', 'LoliHouse', 'MCE', 'Nekomoe kissaten', '(?:Lilith|NC)-Raws', '织梦字幕组']

sites = [rg_0ff,
         rg_1pt,
         rg_52pt,
         rg_audiences,
         rg_azusa,
         rg_beitai,
         rg_btschool,
         rg_carpt,
         rg_chdbits,
         rg_discfan,
         rg_dragonhd,
         rg_eastgame,
         rg_filelist,
         rg_gainbound,
         rg_hares,
         rg_hd4fans,
         rg_hdarea,
         rg_hdatmos,
         rg_hdbd,
         rg_hdchina,
         rg_hddolby,
         rg_hdfans,
         rg_hdhome,
         rg_hdpt,
         rg_hdsky,
         rg_hdtime,
         rg_HDU,
         rg_hdvideo,
         rg_hdzone,
         rg_hhanclub,
         rg_hitpt,
         rg_htpt,
         rg_iptorrents,
         rg_joyhd,
         rg_keepfrds,
         rg_lemonhd,
         rg_mteam,
         rg_nanyangpt,
         rg_nicept,
         rg_oshen,
         rg_ourbits,
         rg_piggo,
         rg_ptchina,
         rg_pterclub,
         rg_pthome,
         rg_ptmsg,
         rg_ptsbao,
         rg_pttime,
         rg_putao,
         rg_soulvoice,
         rg_springsunday,
         rg_tccf,
         rg_tjupt,
         rg_totheglory,
         rg_U2,
         rg_ultrahd,
         rg_other,
         rg_anime]

#  正则 '[-@[]制作组名'，一般制作组前面会有'-'或者'@'或者'['
release_groups = []
for site in sites:
    for release_group in site:
        release_groups.append(release_group)
release_groups = '|'.join(release_groups)
release_groups = re.compile(r"(?<=[-@\[￡])(?:%s)(?=[@.\s\]\[])" % release_groups, re.I)

#  忽略大小写
def rg_match(name, groups):
    return '@'.join(re.findall(groups, name))
