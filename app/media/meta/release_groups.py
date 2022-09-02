import re
#  官组
rp_1pt = []
rp_52pt = []
rp_audiences = ['Audies', 'ADE', 'ADWeb', 'ADAudio', 'ADeBook', 'ADMusic']
rp_avgv = []
rp_beitai = ['BeiTai']
rp_btschool = ['BTSCHOOL', 'BtsHD', 'BtsPAD', 'BtsTV', 'Zone']
rp_chdbits = ['CHD', 'CHDBits', 'CHDTV', 'CHDPAD', 'CHDWEB', 'CHDHKTV', 'StBOX', 'OneHD']
rp_discfan = []
rp_dragonhd = []
rp_eastgame = ['iNT-TLF', 'HALFCD-TLF', 'MiniSD-TLF', 'MiniHD-TLF', 'MiniFHD-TLF', 'TLF']
rp_filelist = []
rp_gainbound = []
rp_hares = ['Hares', 'HaresWEB', 'HaresTV', 'HaresMV']
rp_hd4fans = []
rp_hdarea = ['HDArea', 'EPiC', 'HDATV', 'HDApad']
rp_hdatmos = []
rp_hdbd = []
rp_hdchina = ['HDChina', 'HDCTV', 'HDC', 'k9611', 'tudou', 'iHD']
rp_hddolby = ['Dream', 'DBTV', 'QHstudIo', 'HDo']
rp_hdfans = ['beAst', 'beAstTV']
rp_hdhome = ['HDHome', 'HDH', 'HDHTV', 'HDHPad', 'HDHWEB']
rp_hdsky = ['HDSky', 'HDS', 'HDSWEB', 'HDSTV', 'HDSPad']
rp_hdtime = []
rp_HDU = []
rp_hdzone = []
rp_hitpt = []
rp_htpt = ['HTPT']
rp_iptorrents = []
rp_joyhd = []
rp_keepfrds = ['FRDS']
rp_lemonhd = ['LHD', 'LeagueHD', 'LeagueWEB', 'LeagueTV', 'LeagueCD', ' LeagueMV', 'LeagueNF', 'i18n', 'CiNT']
rp_mteam = ['MTeam', 'MPAD', 'MTeamTV']
rp_nanyangpt = []
rp_nicept = []
rp_oshen = []
rp_ourbits = ['OurBits', 'OurTV', 'FLTTH', 'Ao', 'PbK', 'MGs', 'iLoveTV', 'iLoveHD']
rp_pterclub = ['PTer', 'PTerWEB', 'PTerTV', 'PTerDIY', 'PTerMV', 'PTerGame']
rp_pthome = ['PTHome', 'PTH', 'PTHWEB', 'PTHtv', 'PTHAudio', 'PTHAudio', 'PTHeBook', 'PTHmusic']
rp_ptmsg = []
rp_ptsbao = ['PTsbao', 'OPS', 'FFansBD', 'FFansWEB', 'FFansTV', 'FFansDVD', 'FHDMv']
rp_pttime = []
rp_putao = ['PuTao']
rp_soulvoice = []
rp_springsunday = ['CMCT', 'CMCTV']
rp_tccf = []
rp_tjupt = ['TJUPT']
rp_totheglory = ['TTG', 'WiKi', 'NGB', 'DoA', 'ARiN', 'ExREN']
rp_U2 = []
rp_ultrahd = []

#  其他常见组
rp_other = ['BMDru', 'BeyondHD', 'cfandora', 'FLUX', 'NoGroup', 'TEPES', 'BTN', 'NTb', 'SMURF', 'Ctrlhd']

rp_sites = [rp_1pt,
            rp_52pt,
            rp_audiences,
            rp_avgv,
            rp_beitai,
            rp_btschool,
            rp_chdbits,
            rp_discfan,
            rp_dragonhd,
            rp_eastgame,
            rp_filelist,
            rp_gainbound,
            rp_hares,
            rp_hd4fans,
            rp_hdarea,
            rp_hdatmos,
            rp_hdbd,
            rp_hdchina,
            rp_hddolby,
            rp_hdfans,
            rp_hdhome,
            rp_hdsky,
            rp_hdtime,
            rp_HDU,
            rp_hdzone,
            rp_hitpt,
            rp_htpt,
            rp_iptorrents,
            rp_joyhd,
            rp_keepfrds,
            rp_lemonhd,
            rp_mteam,
            rp_nanyangpt,
            rp_nicept,
            rp_oshen,
            rp_ourbits,
            rp_pterclub,
            rp_pthome,
            rp_ptmsg,
            rp_ptsbao,
            rp_pttime,
            rp_putao,
            rp_soulvoice,
            rp_springsunday,
            rp_tccf,
            rp_tjupt,
            rp_totheglory,
            rp_U2,
            rp_ultrahd,
            rp_other]

#  正则 '[-@[]制作组名'，一般制作组前面会有'-'或者'@'或者'['
rp_groups = []
for rp_site in rp_sites:
    for rp_group in rp_site:
        rp_groups.append("[-@[]" + rp_group)


#  忽略大小写
def rp_match(name, groups):
    for group in groups:
        res = re.findall(group, name, re.I)
        if res:
            return res
    return ""
