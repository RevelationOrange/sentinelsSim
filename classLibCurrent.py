try:
    from numpy import random as rng
    rngoffset = 0
except:
    import random as rng
    rngoffset = 1
import argparse


class idTracker:
    def __init__(self):
        self.num = 0
    def id(self):
        self.num += 1
        return self.num-1
gid = idTracker()

def canIntConvert(x):
    try:
        int(x)
        return True
    except:
        return False

class joinArgs(argparse.Action):
    def __call__(self, parser, namespace, values, *args, **kwargs):
        setattr(namespace, self.dest, ' '.join(values))

cardParser = argparse.ArgumentParser()
cardParser.add_argument("-name", nargs='+', action=joinArgs)
cardParser.add_argument("-text", nargs='+', action=joinArgs)
cardParser.add_argument('-owner', dest='owner', nargs='+', action=joinArgs)
cardParser.add_argument("-type")
cardParser.add_argument("-keywords", nargs='+', default=[])
cardParser.add_argument("-action", dest='actions', nargs='+', action='append', default=[])
cardParser.add_argument("-power", dest='powers', nargs='+', action='append', default=[])
cardParser.add_argument("-effect", dest='effects', nargs='+', action='append', default=[])
cardParser.add_argument("-hp", type=int, default=None)

actionParser = argparse.ArgumentParser(prefix_chars='+')
actionParser.add_argument("+source")
actionParser.add_argument("+type")
actionParser.add_argument("+givetype")
actionParser.add_argument("+target", dest='targets', nargs='+', action='append')
actionParser.add_argument("+givetarget", dest='givetargets', nargs='+', action='append')

targetParser = argparse.ArgumentParser(prefix_chars='@')
targetParser.add_argument("@areas", nargs='+')
targetParser.add_argument("@sections", nargs='+')
targetParser.add_argument("@restrictions", nargs='+', default=[])
targetParser.add_argument("@pick")
targetParser.add_argument("@xquants")
targetParser.add_argument("@quantity", dest='quantities', nargs='+', action='append')
## maybe have a separate thing for effects, since they're pretty complex

effPowParser = argparse.ArgumentParser(prefix_chars='~')

def eq(x,y):
    return x == y

def ne(x,y):
    return x != y

def lt(x,y):
    return x < y

def le(x,y):
    return x <= y

def gt(x,y):
    return x > y

def ge(x,y):
    return x >= y

def within(x,y):
    return x >= y[0] and x <= y[1]

def nothing(x):
    return x

testTypeDict = {'==':eq, '!=':ne, '<':lt, '<=':le, '>':gt, '>=':ge, 'range':within, 'noth':nothing}

def kwTest(res, default=True):
    def tst(c):
        if res in c.keywords:
            return default
        else:
            return not default
    return tst

def ifHpTest(default=True):
    def tst(c):
        if c.maxHP:
            return default
        else:
            return not default
    return tst

def hpTest(tstType, val):
    def tst(c):
        if c.maxHP:
            return testTypeDict[tstType](c.currentHP, val)
        else:
            return False
    return tst

class Target:
    def __init__(self, parseStr):
        target = targetParser.parse_args(parseStr)
        if target.areas == ['any']:
            self.areas = ['villain', 'hero', 'environment']
        else:
            self.areas = target.areas
        self.sections = target.sections
        if target.restrictions:
            # print('restrictions created:',target.restrictions)
            self.restrictions = [target.restrictions[0]]
        else:
            self.restrictions = []
        defaultReturn = True
        i = 1
        while i < len(target.restrictions):
        # for i in range(len(target.restrictions[1:])):
        # for restr in target.restrictions[1:]:
            restr = target.restrictions[i]
            if restr == 'not':
                defaultReturn = False
            elif restr == '==':
                defaultReturn = True
            elif restr == 'hp':
                if len(target.restrictions) > i+1:
                    cmp,val = target.restrictions[i+1],target.restrictions[i+2]
                    if cmp in testTypeDict and canIntConvert(val):
                        i += 2
                        self.restrictions.append(hpTest(cmp, val))
                    else:
                        self.restrictions.append(ifHpTest(defaultReturn))
                else:
                    self.restrictions.append(ifHpTest(defaultReturn))
            else:
                self.restrictions.append(kwTest(restr, defaultReturn))
            i += 1
        self.quantities = target.quantities
        self.xquants = target.xquants
        self.pick = target.pick
    def __repr__(self):
        reprStr = ""
        if self.areas:
            reprStr += ', '.join(self.areas) + ' cards '
        if self.restrictions:
            reprStr += 'with kws ' + (self.restrictions[0]) + ', '
        if self.quantities:
            for q in self.quantities:
                reprStr += ", {}".format(' '.join(q))
        return reprStr

class Action:
    def __init__(self, parseStr):
        action = actionParser.parse_args(parseStr)
        self.source = action.source
        self.actionType = action.type
        self.giveType = action.givetype
        self.targets = []
        for t in action.targets:
            self.targets.append(Target(t))
        self.giveTargets = []
        if action.givetargets:
            for gt in action.givetargets:
                self.giveTargets.append(Target(gt))
        self.createdStr = parseStr
    def given(self):
        gA = Action(self.createdStr)
        gA.actionType = gA.giveType
        return gA
    def __repr__(self):
        return "{}, {}, {}".format(self.source, self.actionType, ', '.join([x.__repr__() for x in self.targets]))

class Card:
    def __init__(self, parseStr):
        card = cardParser.parse_args(parseStr.split())
        self.name = card.name
        self.text = card.text
        self.type = card.type
        self.keywords = card.keywords
        self.currentHP = card.hp
        self.maxHP = card.hp
        self.actions = []
        for act in card.actions:
            self.actions.append(Action(act))
        self.powers = []
        if card.powers:
            for pow in card.powers:
                self.powers.append(Action(pow))
        self.owner = card.owner
        self.actFxns = {'damage': self.takeDamage, 'heal': self.heal}
        self.uid = gid.id()
    def setOwner(self, o):
        self.owner = o
    def takeDamage(self, x):
        self.currentHP -= max(x, 0)
        return self.currentHP < 1, self.owner
    def heal(self, x):
        self.currentHP += max(x, 0)
        self.currentHP = min(self.currentHP, self.maxHP)
        # limit current to max hp
    def __repr__(self):
        rstr = "{} ({}): {}".format(self.name, ', '.join(self.keywords), self.text)
        if self.maxHP:
            rstr += " {}/{} hp".format(self.currentHP, self.maxHP)
        return rstr

class PlayArea:
    def __init__(self, player, hero, deckList):
        self.player = player
        self.character = hero
        for c in deckList:
            c.setOwner(self.character.name)
        self.deck = deckList
        self.inPlay = []
        self.hand = []
        self.trash = []
        self.effects = []
        self.powers = []
        self.shuffle()
        if not self.character.type:
            self.paType = 'environment'
        else:
            self.paType = self.character.type
        self.actFxns = {'shuffle': self.shuffle, 'draw': self.draw, 'play': self.play, 'destroy': self.destroy,
                        'trash': self.putInTrash, 'deck': self.putInDeck}
    def shuffle(self):
        newDeck = []
        while self.deck:
            newDeck.append(self.deck.pop(rng.randint(0, len(self.deck)-rngoffset)))
        self.deck = newDeck
    def draw(self, x):
        for _ in range(x):
            if not self.deck:
                self.shuffle()
            if self.deck:
                self.hand.append(self.deck.pop(0))
    def setH(self, H):
        for card in self.deck:
            ## probly also check hp for H
            for act in card.actions:
                for t in act.targets + act.giveTargets:
                    ## definitely also check damage values, that's gonna show up a lot in the villain cards, obvs
                    if t.xquants == 'H':
                        t.xquants = H
    def play(self, n=0):
        if n < 0:
            card = self.deck.pop(n+1)
        else:
            card = self.hand.pop(n)
        return self, card, card.actions, True
    def destroy(self, card):
        self.inPlay.remove(card)
    def putInTrash(self, card):
        self.trash.append(card)
    def putInDeck(self, card, location):
        if location == 'top':
            self.deck.insert(0, card)
        elif location == 'bot':
            self.deck.append(card)
    def shuffleTrashIntoDeck(self):
        self.deck += self.trash
        self.trash = []
        self.shuffle()
    def __repr__(self):
        return "{} playing {}".format(self.player, self.character.name)


class Game:
    def __init__(self):
        self.villains = []
        self.villainDict = {}
        self.heroes = []
        self.heroDict = {}
        self.environment = None
        self.turnOrder = []
        self.actFxns = {'damage': self.damageHandler, 'destroy': self.destroyHandler, 'deck': self.deckHandler, 'heal': self.healHandler}
    def addHero(self, h):
        if len(self.heroDict) < 5:
            self.heroDict[h.character.name] = h
            self.heroes.append(h)
        else:
            print("No more than 5 heroes allowed in a game.")
    def addVillain(self, vil):
        if len(self.villainDict) < 5:
            self.villainDict[vil.character.name] = vil
            self.villains.append(vil)
        else:
            print("No more than 5 villains allowed in a game.")
    def setEnvironment(self, e):
        self.environment = e
    def setupGame(self):
        if len(self.heroes) < 1:
            print("At least 3 heroes required to play.")
        elif len(self.villains) != len(self.heroes):
            print("In a team villains game, you have to have the same number of heroes and villains.")
        else:
            i = 0
            for h in self.heroes:
                if i < len(self.villains):
                    self.turnOrder.append(self.villains[i])
                    i += 1
                self.turnOrder.append(h)
            self.turnOrder.append(self.environment)
        ## do villain setup stuff; figure out how that's determined later
        for h in self.heroes:
            h.draw(4)
            h.setH(len(self.heroes))
        self.environment.setH(len(self.heroes))
    def actionHandler(self, source, card, actions, played=False):
        print(source, "is doing actions from", card)
        for act in actions:
            if act.source == 'self':
                actionSource = {'card': card}
            elif act.source == 'char':
                actionSource = {'card': source.character}
            elif act.source == 'player':
                actionSource = {'card': source}
            else:
                ## do getTargets and pick the source
                print('unexpected action source type (character instead of char maybe?)')
            actionSource['effects'] = source.effects
            actionSource['area'] = source
            print(act)
            print(act.actionType)
            if act.actionType == 'draw':
                for target in act.targets:
                    actionTargets = []
                    if target.areas == ['self']:
                        actionTarget = source
                    else:
                        ## do getTargets and add them to actionTargets list
                        pass
                    for q in target.quantities:
                        if 'opt' in q:
                            skp = int(input('enter 0 to draw, 1 to skip '))
                            if skp == 0:
                                actionTarget.actFxns[act.actionType](int(q[0]))
                        else:
                            actionTarget.actFxns[act.actionType](int(q[0]))
            elif act.actionType in ['damage', 'destroy', 'deck', 'heal']:
                for target in act.targets:
                    print(act.actionType, 'target:', target)
                    tAs = []
                    for ta in target.areas:
                        if ta == 'self':
                            tAs.append(actionSource['area'].character.name)
                        else:
                            tAs.append(ta)
                    targetList = self.getTargets(tAs, target.sections, target.restrictions)
                    if target.pick:
                        if target.pick == 'hp':
                            targetList = sorted(targetList, key=lambda x: x['card'].currentHP)
                    quants = []
                    if target.xquants:
                        if target.xquants == 'all':
                            for _ in targetList:
                                quants.append(target.quantities[0])
                        else:
                            for _ in range(int(target.xquants)):
                                quants.append(target.quantities[0])
                    else:
                        quants = target.quantities.copy()
                    for q in quants:
                        if target.pick:
                            i = int(q[-1])
                        else:
                            if 'opt' in q:
                                targetList.append('skip')
                            if len(targetList) == 0:
                                print('no valid targets')
                                continue
                            i = -1
                            print('target options:', targetList)
                            while i not in range(len(targetList)):
                                i = int(input('enter target number: '))
                        if len(targetList) == 0:
                            print('no valid targets')
                            continue
                        actionTarget = targetList.pop(i)
                        print('target picked:', actionTarget)
                        if 'skip' in targetList:
                            targetList.remove('skip')
                        if actionTarget == 'skip':
                            if 'gate' in q:
                                break
                            continue
                        self.actFxns[act.actionType](actionSource, actionTarget, *q)
            elif act.actionType == 'give':
                givenAction = act.given()
                for target in act.giveTargets:
                    print(act.actionType, 'target:', target)
                    tAs = []
                    for ta in target.areas:
                        if ta == 'self':
                            tAs.append(actionSource['area'].character.name)
                        else:
                            tAs.append(ta)
                    targetList = self.getTargets(tAs, target.sections, target.restrictions)
                    if target.pick:
                        ## sort the target list by whatever the criteria, like cards in play or whatever
                        pass
                    quants = []
                    if target.xquants:
                        if target.xquants == 'all':
                            for _ in targetList:
                                quants.append(target.quantities[0])
                        else:
                            for _ in range(int(target.xquants)):
                                quants.append(target.quantities[0])
                    else:
                        quants = target.quantities.copy()
                    for q in quants:
                        if target.pick:
                            i = int(q[-1])
                        else:
                            if 'opt' in q:
                                targetList.append('skip')
                            if len(targetList) == 0:
                                print('no valid targets')
                                continue
                            i = -1
                            print('target options:', targetList)
                            while i not in range(len(targetList)):
                                i = int(input('enter target number: '))
                        if len(targetList) == 0:
                            print('no valid targets')
                            continue
                        actionTarget = targetList.pop(i)
                        print('target picked:', actionTarget)
                        if 'skip' in targetList:
                            targetList.remove('skip')
                        if actionTarget == 'skip':
                            if 'gate' in q:
                                break
                            continue
                        self.actionHandler(actionTarget['area'], actionTarget['card'], [givenAction])
            elif act.actionType == 'put':
                ## the card gets put into play based on the put's targeting
                ## then, if there's an associated effect, the put target is used to setup that effect
                ## and the effect has its own targeting to determine where to put it
                for target in act.targets:
                    print(act.actionType, 'target:', target)
                    tAs = []
                    for ta in target.areas:
                        if ta == 'self':
                            tAs.append(actionSource['area'].character.name)
                        else:
                            tAs.append(ta)
                    putTargetList = self.getTargets(tAs, target.sections, target.restrictions)
                    if target.pick:
                        pass
                    else:
                        if len(putTargetList) == 0:
                            print('no valid targets')
                            continue
                        i = -1
                        print('target options:', putTargetList)
                        while i not in range(len(putTargetList)):
                            i = int(input('enter target number: '))
                        putTarget = putTargetList.pop(i)
                        putTarget['area'].inPlay.append(actionSource['card'])
                        # if card.effects:
                        #     for eff in card.effects:
                        #         pass
                        if card.powers:
                            for pow in card.powers:
                                putTarget['area'].powers.append([pow, card])
        if played:
            if 'one-shot' in card.keywords:
                if card.type == 'environment':
                    self.environment.actFxns['trash'](card)
                elif card.owner in self.heroDict:
                    self.heroDict[card.owner].actFxns['trash'](card)
                else:
                    self.villainDict[card.owner].actFxns['trash'](card)
    def damageHandler(self, source, target, dmg, dmgType, *excess):
        ## go through source's effects to modify damage
        for eff in source['effects']:
            pass
        ## go through target's effects to modify damage
        for eff in target['effects']:
            pass
        destroyed, owner = target['card'].actFxns['damage'](int(dmg))
        if destroyed:
            self.destroyHandler(source, target)
    def healHandler(self, source, target, healing, *excess):
        for eff in source['effects']:
            pass
        for eff in target['effects']:
            pass
        target['card'].actFxns['heal'](int(healing))
    def destroyHandler(self, source, target, *excess):
        for eff in source['effects']:
            pass
        for eff in target['effects']:
            pass
        owner = target['card'].owner
        if owner:
            target['area'].actFxns['destroy'](target['card'])
            ## check here (or maybe before if owner) for trash redirection effects
            if owner in self.heroDict:
                self.heroDict[owner].actFxns['trash'](target['card'])
            elif owner in self.villainDict:
                self.villainDict[owner].actFxns['trash'](target['card'])
            else:
                self.environment.actFxns['trash'](target['card'])
        else:
            ## do incapacitated/flip stuff
            self.checkWinLose()
    def deckHandler(self, source, target, deckLocation, *excess):
        for sec in [target['area'].inPlay, target['area'].trash, target['area'].deck]:
            for card in sec:
                if card.uid == target['card'].uid:
                    sec.remove(card)
        if target['card'].owner in self.villainDict:
            self.villainDict[target['card'].owner].actFxns['deck'](target['card'], deckLocation)
        elif target['card'].owner in self.heroDict:
            self.heroDict[target['card'].owner].actFxns['deck'](target['card'], deckLocation)
        else:
            self.environment.actFxns['deck'](target['card'], deckLocation)
    def getTargets(self, checkAreas, checkSections, restrictions):
        ## need to fix so that for the 'card type' 'players', it actually returns players and not specific cards
        targList = []
        check = []
        print('getting targets,', checkAreas)
        for a in self.turnOrder:
            if a.paType in checkAreas:
                check.append(a)
            elif a.character.name in checkAreas:
                check.append(a)
        for area in check:
            if 'playarea' in checkAreas:
                ## also do checks here for stuff like 'most cards in play' etc.
                targList.append({'card': area.character, 'area': area, 'effects': area.effects})
            else:
                areaCards = []
                for csec in checkSections:
                    if csec == 'char':
                        areaCards.append(area.character)
                    elif csec == 'inplay':
                        areaCards += area.inPlay
                    elif csec == 'deck':
                        areaCards += area.deck
                    elif csec == 'trash':
                        areaCards += area.trash
                for card in areaCards:
                    if restrictions:
                        ors = False
                        ands = True
                        for r in restrictions[1:]:
                            if r(card):
                                ors = True
                            else:
                                if restrictions[0] == 'and':
                                    ands = False
                        if ors and ands:
                            targList.append({'card': card, 'area': area, 'effects': area.effects})
                    else:
                        targList.append({'card': card, 'area': area, 'effects': area.effects})
        return targList
    def checkWinLose(self):
        lose = True
        for hero in self.heroes:
            if hero.character.currentHP > 0:
                lose = False
        if lose:
            print("you lose!")
            exit()
        win = True
        for vil in self.villains:
            if vil.character.currentHP > 0:
                win = False
        if win:
            print('you win!')
            exit()
