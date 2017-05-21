from classLibCurrent import *


acstr = "-name Aquatic Correspondence -text Draw 3 cards. -type hero -keywords one-shot -action +source self +type draw +target @areas self @quantity 3"

blstr = "-name Ball Lightning -text Tempest deals 1 target 4 lightning damage. You may destroy up to 2 ongoing cards."
blstr += " -type hero -keywords one-shot -action +source char +type damage +target @areas any @sections char inplay @restrictions or hp @quantity 4 lightning"
blstr += " -action +source self +type destroy +target @areas any @sections inplay @restrictions and ongoing not indestructible @quantity opt @quantity opt"

clstr = "-name Chain Lightning -text Tempest deals 1 Target 4 Lightning Damage. Tempest may deal a second Target 3 Lightning Damage. Tempest may deal a third Target 2 Lightning Damage."
clstr += " -type hero -keywords one-shot -action +source char +type damage +target @areas any @sections char inplay @restrictions or hp"
clstr += " @quantity 4 lightning @quantity 3 lightning opt @quantity 2 lightning opt"

ffstr = "-name Flash Flood -text Destroy up to 2 Environment cards. -type hero -keywords one-shot -action +source self"
ffstr += " +type destroy +target @areas environment @sections inplay @xquants 2 @quantity opt"

itsstr = "-name Into the Stratosphere -text Select 1 non-indestructible Villain card in play, other than a Character card, and put it on top of the Villain deck. Tempest deals the Villain Target with the highest HP 2 Projectile Damage. -type hero -keywords one-shot"
itsstr += " -action +source self +type deck +target @areas villain @sections inplay @restrictions or not indestructible @quantity top"
itsstr += " -action +source char +type damage +target @areas villain @sections char inplay @pick hp @restrictions or hp @quantity 2 projectile -1"

lsstr = "-name Lightning Slash -text Tempest deals 1 target 5 lightning damage. -type hero -keywords one-shot -action +source char +type damage +target @areas any @sections char inplay @restrictions or hp @quantity 5 lightning"

rftdstr = "-name Reclaim from the Deep -text Each player may take a card from their trash and put it on top of their Hero deck. You may draw a card."
rftdstr += " -type hero -keywords one-shot -action +source self +type give +givetype deck +target @areas self @sections trash @quantity top opt"
rftdstr += " +givetarget @areas playarea hero @xquants H @quantity 1 -action +source self +type draw +target @areas self @quantity 1 opt"

cdstr = "-name Cleansing Downpour -text Power: Each Hero Target regains 2 HP. -type hero -keywords ongoing -action +source self +type put"
cdstr += " +target @areas playarea self @sections inplay @quantity 1 -power ~action +source self +type heal +target @areas hero"
cdstr += " @sections char inplay @restrictions or hp @xquants all @quantity 2"

ghsstr = "-name Grievous Hail Storm -text Power: Tempest deals each non-Hero Target 2 Cold Damage. -type hero -keywords ongoing"
ghsstr += " -action +source self +type put +target @areas playarea self @sections inplay @quantity 1 -power ~action +source char"
ghsstr += " +type damage +target @areas villain environment @sections char inplay @restrictions or hp @xquants all @quantity 2 cold"

lhstr = "-name Localized Hurricane -text Increase Damage dealt to Tempest by 1. Power: Tempest deals up to 2 Targets 3"
lhstr += " Projectile Damage each. You may draw 2 cards. Power: Destroy this card. -type hero -keywords ongoing -action"
lhstr += " +source self +type put +target @areas playarea self @sections inplay @quantity 1 -power ~action +source char"
lhstr += " +type damage +target @areas any @sections char inplay @restrictions or hp @xquants 2 @quantity 3 projectile opt"
lhstr += " ~action +source self +type draw +target @areas self @quantity 2 opt"
lhstr += " -power ~action +source self +type destroy +target @areas self @sections inplay @restrictions or self @quantity 1"

AC = Card(acstr)
BL = Card(blstr)
CL = Card(clstr)
FF = Card(ffstr)
ItS = Card(itsstr)
LS = Card(lsstr)
RftD = Card(rftdstr)
CD = Card(cdstr)
GHS = Card(ghsstr)
LH = Card(lhstr)
# AC.setOwner('Tempest')
# LB.setOwner('Tempest')
tdeck = [RftD]*20 + [LH]*20
tempest = PlayArea('derp', Card('-name Tempest -text Squall: Tempest deals all non-hero targets 1 Projectile damage. -type hero -hp 26'), tdeck)
vdeck = [Card('-name generic villain card -text do a bad thing -type villain -keywords one-shot')]*40
vil = PlayArea('AI', Card('-name baron derp -text herp derp -type villain -hp 10'), vdeck)
edeck = [Card('-name generic environment card -text do a thing -type environment -keywords one-shot')]*15
env = PlayArea('AI', Card('-name megaderpolis -text env'), edeck)

thisGame = Game()
thisGame.addHero(tempest)
thisGame.addVillain(vil)
thisGame.setEnvironment(env)
thisGame.setupGame()

test0 = Card("-name generic ongoing card -text sits here as an ongoing -keywords ongoing -type villain -owner baron derp")
test1 = Card("-name generic target card -text sits here as a target -type villain -owner baron derp -hp 2")
test2 = Card("-name generic environment card -text sits here as a card -type environment -owner megaderpolis")
# AC.setOwner('Tempest')
# thisGame.heroes[0].trash.append(AC)
thisGame.villains[0].inPlay.append(test0)
thisGame.villains[0].inPlay.append(test1)
# thisGame.villains[0].inPlay.append(test1)
thisGame.environment.inPlay.append(test2)
thisGame.environment.inPlay.append(test2)

if 1:
    for _ in range(2):
        for pl in thisGame.turnOrder:
            print(pl)
            if pl.character.type == 'hero':
                # play phase
                print(pl.hand)
                i = -1
                while i not in range(len(pl.hand)):
                    i = int(input('enter card number: '))
                playCard = pl.hand[i]
                print(playCard)
                thisGame.actionHandler(*pl.play(i))
                print('after hand:', pl.hand)
                print('hand len:', len(pl.hand))
                # power phase
                print('-powers phase-')
                if pl.powers:
                    ## make a temp list of powers, pop as used (in case multiple powers can be used in a turn)
                    print([x[0] for x in pl.powers])
                    i = -1
                    while i not in range(len(pl.powers)):
                        i = int(input('enter power number: '))
                    thisGame.actionHandler(pl, pl.powers[i][1], pl.powers[i][0])
                else:
                    print('(no usable powers)')
            else:
                thisGame.actionHandler(*pl.play(-1))
            print(pl.inPlay)
            print(pl.trash)
            print()


print('player hand:',thisGame.heroes[0].hand)
print('pl hand len:',len(thisGame.heroes[0].hand))
print('pl powers:', thisGame.heroes[0].powers)
print('vil trash:',thisGame.villains[0].trash)
print('player trash:',thisGame.heroes[0].trash)
print('env trash:',thisGame.environment.trash)
print('player hp:',thisGame.heroes[0].character.currentHP)
print('villain hp:',thisGame.villains[0].character.currentHP)
print('villain in play:',thisGame.villains[0].inPlay)
