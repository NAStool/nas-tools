import re

#  官组
rg_1pt = []
rg_52pt = []
rg_audiences = ['Audies', 'ADE', 'ADWeb', 'ADAudio', 'ADeBook', 'ADMusic']
rg_avgv = []
rg_beitai = ['BeiTai']
rg_btschool = ['BTSCHOOL', 'BtsHD', 'BtsPAD', 'BtsTV', 'Zone']
rg_chdbits = ['CHD', 'CHDBits', 'CHDTV', 'CHDPAD', 'CHDWEB', 'CHDHKTV', 'StBOX', 'OneHD', 'Lee', 'xiaopie']
rg_discfan = []
rg_dragonhd = []
rg_eastgame = ['iNT-TLF', 'HALFCD-TLF', 'MiniSD-TLF', 'MiniHD-TLF', 'MiniFHD-TLF', 'TLF']
rg_filelist = []
rg_gainbound = []
rg_hares = ['Hares', 'HaresWEB', 'HaresTV', 'HaresMV']
rg_hd4fans = []
rg_hdarea = ['HDArea', 'EPiC', 'HDATV', 'HDApad']
rg_hdatmos = []
rg_hdbd = []
rg_hdchina = ['HDChina', 'HDCTV', 'HDC', 'k9611', 'tudou', 'iHD']
rg_hddolby = ['Dream', 'DBTV', 'QHstudIo', 'HDo']
rg_hdfans = ['beAst', 'beAstTV']
rg_hdhome = ['HDHome', 'HDH', 'HDHTV', 'HDHPad', 'HDHWEB']
rg_hdsky = ['HDSky', 'HDS', 'HDSWEB', 'HDSTV', 'HDSPad', 'AQLJ']
rg_hdtime = []
rg_HDU = []
rg_hdzone = []
rg_hitpt = []
rg_htpt = ['HTPT']
rg_iptorrents = []
rg_joyhd = []
rg_keepfrds = ['FRDS', 'Yumi', 'cXcY']
rg_lemonhd = ['LHD', 'LeagueHD', 'LeagueWEB', 'LeagueTV', 'LeagueCD', ' LeagueMV', 'LeagueNF', 'i18n', 'CiNT']
rg_mteam = ['MTeam', 'MPAD', 'MTeamTV']
rg_nanyangpt = []
rg_nicept = []
rg_oshen = []
rg_ourbits = ['OurBits', 'OurTV', 'FLTTH', 'Ao', 'PbK', 'MGs', 'iLoveTV', 'iLoveHD']
rg_pterclub = ['PTer', 'PTerWEB', 'PTerTV', 'PTerDIY', 'PTerMV', 'PTerGame']
rg_pthome = ['PTHome', 'PTH', 'PTHWEB', 'PTHtv', 'PTHAudio', 'PTHAudio', 'PTHeBook', 'PTHmusic']
rg_ptmsg = []
rg_ptsbao = ['PTsbao', 'OPS', 'FFansBD', 'FFansWEB', 'FFansTV', 'FFansDVD', 'FHDMv']
rg_pttime = []
rg_putao = ['PuTao']
rg_soulvoice = []
rg_springsunday = ['CMCT', 'CMCTV']
rg_tccf = []
rg_tjupt = ['TJUPT']
rg_totheglory = ['TTG', 'WiKi', 'NGB', 'DoA', 'ARiN', 'ExREN']
rg_U2 = []
rg_ultrahd = []

#  其他常见组
rg_other = ['BMDru', 'BeyondHD', 'cfandora', 'FLUX', 'NoGroup', 'TEPES', 'BTN', 'NTb', 'SMURF', 'Ctrlhd', 'CMRG', 'EVO', 'HONE', 'NTG']

sites = [rg_1pt,
         rg_52pt,
         rg_audiences,
         rg_avgv,
         rg_beitai,
         rg_btschool,
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
         rg_hdsky,
         rg_hdtime,
         rg_HDU,
         rg_hdzone,
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
         rg_other]

#  正则 '[-@[]制作组名'，一般制作组前面会有'-'或者'@'或者'['
release_groups = '|'
for site in sites:
    for release_group in site:
        release_groups = release_groups + "(?<=[-@[￡])" + release_group + "(?=[@.\s\][])" + "|"
release_groups = re.compile(r"" + release_groups[1:-1], re.I)


#  忽略大小写
def rg_match(name, groups):
    res_l = []
    res_s = ""
    res_l = re.findall(groups, name)
    if len(res_l) == 1:
        return res_l[0]
    elif len(res_l) > 1:
        for res in res_l:
            res_s = res_s + "@" + res
        return res_s[1:]
    else:
        return ""
