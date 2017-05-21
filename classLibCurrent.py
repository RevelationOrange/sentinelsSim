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


# in order to create a card (and action, and target), I used command line-style arguments, with options used to make
# each attribute of the card/action/target
# name and text of a card need to be single strings, so they're joined together
# owner can be 'absolute zero', so it also needs to be a joined string
# actions are appended to a list and added one at a time, using + for the next prefix (the action options)
# powers and effects will work similarly, but will consist of one or more actions; their implementation needs to be fixed
cardParser = argparse.ArgumentParser()
cardParser.add_argument("-name", nargs='+', action=joinArgs)
cardParser.add_argument("-text", nargs='+', action=joinArgs)
cardParser.add_argument("-owner", dest='owner', nargs='+', action=joinArgs)
cardParser.add_argument("-type")
cardParser.add_argument("-keywords", nargs='+', default=[])
cardParser.add_argument("-action", dest='actions', nargs='+', action='append', default=[])
cardParser.add_argument("-power", dest='powers', nargs='+', action='append', default=[])
cardParser.add_argument("-effect", dest='effects', nargs='+', action='append', default=[])
cardParser.add_argument("-hp", type=int, default=None)

# targets are added like actions above, with @ used as a prefix for target options
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

powerParser = argparse.ArgumentParser(prefix_chars='~')
powerParser.add_argument("~action", dest='actions', nargs='+', action='append', default=[])

# (each option will be explained in detail in the class definition)

# these definitions are put into a dictionary so they can be used for comparisons, based on text options for restrictions in targets
# (I feel like there should be a better way to do this, but I don't know what it is)
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

# these functions are used to create custom tests, that a card is passed into (test(card) returns a bool)
# stuff like, does it have x keyword, does it have hp at all, is its hp over/under/whatever some number
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

def idTest(idnum, default=True):
    def tst(c):
        if c.uid == idnum:
            return default
        else:
            return not default
    return tst

# the Target class, for storing criteria used to pick the target of an action
# creating a target is done via command line-like arguments (same for actions and cards)
# @areas: the types of play areas that can be targeted- villain, hero, or environment ('any' is replaced by all 3)
# @sections: the sections in a play area that can be targeted- inPlay, character, hand (maybe?), deck, trash
# @restrictions: criteria to check the card/area for
# the first thing here (in the parse string) will be either and or or. this will tell the getTargets function what type
# of search it's doing. ex: a card that says 'destroy one ongoing on equipment card' will have an or in restrictions, so
# when checking cards, they need only have one of either ongoing or equipment in the keywords. ex: 'destroy an ongoing
# card' will have and in restrictions, so any card needs to have ongoing as a keyword and not indestructible
# then, for each restriction, a test function is created. the default check type is ==, which will be changed when 'not'
# is encountered in the restrictions. if the restriction  is 'hp', by itself, a test will be created that checks if the
# card has an hp value, 'hp < 5' for example will check if the card's hp is less than 5 (this is where testTypeDict is
# used). anything else will be assumed to be a keyword to be checked.
# @quantities: a list of values to use for whatever the action is; for draw actions, it's just a number, for damage,
# it's a number and the damage type. if opt is present, a 'skip' option is added when picking targets; if 'gate' is
# present, picking skip cancels the remaining quantities that might be present; if @pick was specified for this target,
# the last entry of the quantity will be the index number to choose from the target list.
# @xquants: this is a way to implement a variable number of quantities for the target (or just a convenient way to
# duplicate them). if it's a number (or H, which will be converted to a number on game start), that many duplicates of
# the first quantity will be made; if it's 'all', the number used will be the length of the target list
# @pick: when the targets need to be sorted, such as when a card says 'deal the highest hp hero target 2 damage', pick
# is specified with the type of criteria; hp can be used for cards, ncardsInPlay for play areas (for example; not yet
# implemented)
class Target:
    def __init__(self, parseStr, idn):
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
            elif restr == 'self':
                print('adding self target restriction')
                self.restrictions.append(idTest(idn, defaultReturn))
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

# the Action class, for storing instructions to perform corresponding to an action (like 'draw 3 cards')
# +source: the origin of the action; 'self' (applied to a play area or card) or 'char' (applied to the character of the
# play area). I haven't really cemented this yet; ex: when actions happen that aren't played by a card, not sure
# exactly what the source would be in all cases.
# +type: the type of action- draw, damage, destroy, heal, deck (put a card in a deck), give (transfer the action to
# another target), put (designate where an ongoing card goes into play)
# +givetype: when it's a give action, the action type here is the type that's given
# +target: add a target object for the action (see above)
# +givetarget: same as +target, but defines targeting for a give action
# createdStr is stored for later use when a give action needs to be created, and its type replaced with its givetype
# which is what given() does
class Action:
    def __init__(self, parseStr, idn=0):
        action = actionParser.parse_args(parseStr)
        self.source = action.source
        self.actionType = action.type
        self.giveType = action.givetype
        self.targets = []
        for t in action.targets:
            self.targets.append(Target(t, idn))
        self.giveTargets = []
        if action.givetargets:
            for gt in action.givetargets:
                self.giveTargets.append(Target(gt, idn))
        self.createdStr = parseStr
    def given(self):
        gA = Action(self.createdStr)
        gA.actionType = gA.giveType
        return gA
    def __repr__(self):
        return "{}, {}, {}".format(self.source, self.actionType, ', '.join([x.__repr__() for x in self.targets]))

# the Card class, for storing all information about a card- name, descriptive text, actions, etc.
# -name, -text: pretty self explanatory
# -type: hero, villain, or environment
# -keywords: ongoing, equipment, one-shot, etc.
# current and max hp are set to the given -hp value, or 'None' if it's not given
# -action: add an action object for the card (see above)
# -power: add a power to the card (this is still being worked out)
# -owner: the name of the hero/villain/environment that owns the card (mostly used to determine the trash it goes to)
# setOwner() can be used to change the owner after the card is created- likely, this will be used when a player is
# created, going through a deck, creating and setting the owner for each card
# takeDamage() and heal() are functions so that cards themselves can handle their hp
class Card:
    def __init__(self, parseStr):
        card = cardParser.parse_args(parseStr.split())
        self.uid = gid.id()
        self.name = card.name
        self.text = card.text
        self.type = card.type
        self.keywords = card.keywords
        self.currentHP = card.hp
        self.maxHP = card.hp
        self.actions = []
        for act in card.actions:
            self.actions.append(Action(act, self.uid))
        self.powers = []
        if card.powers:
            for pow in card.powers:
                p = powerParser.parse_args(pow)
                powActs = []
                for pAct in p.actions:
                    powActs.append(Action(pAct, self.uid))
                self.powers.append(powActs)
        self.owner = card.owner
        self.actFxns = {'damage': self.takeDamage, 'heal': self.heal}
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

# the PlayArea class, for storing info pertaining to a play area: deck, cards in play, hand, trash, character card(s), etc.
# player is the name of who's playing (once fully automated, will likely just be 'human' or something
# character is the main character card(s), that determine if you're still in play; none for the environment play area
# the deck is the list of your cards, and when a play area is created each card's owner is set
# the effects list tracks ongoing effects, like 'all damage this turn is melee' or 'when x card is destroyed, deal y
# damage to z'
# the powers list tracks the powers that can be used
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
        # draw(x) takes x cards from the top of the deck and puts in into the hand
        for _ in range(x):
            if not self.deck:
                self.shuffle()
            if self.deck:
                self.hand.append(self.deck.pop(0))
    def setH(self, H):
        # setH(H) goes through every card and replaces H with the value it will be for the rest of the game
        for card in self.deck:
            ## probly also check hp for H
            for act in card.actions:
                for t in act.targets + act.giveTargets:
                    ## definitely also check damage values, that's gonna show up a lot in the villain cards, obvs
                    if t.xquants == 'H':
                        t.xquants = H
    def play(self, n=0):
        # if n is >= 0, it's the index of the card to play in the hand list
        # if it's -1, play the card from the top of the deck; -2, play the card from the bottom of the deck
        # the play area, card, and its actions are returned to the action handler, with the flag that this is a card
        # being played (so it knows to trash it afterwards [if it's a one-shot])
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


# the Game class, for overseeing everything, basically
# villains and villainDict: an ordered list (for turn order purposed) and a dictionary (for ease of access) with all the
# villains added to the game. same for heroes and heroDict.
# there can only ever be one environment, so that one doesn't need to be a list
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
        # when a hero (a play area) is added, check if there are less than 5 heroes already before adding; if so, add h
        # to the hero list and dict
        if len(self.heroDict) < 5:
            self.heroDict[h.character.name] = h
            self.heroes.append(h)
        else:
            print("No more than 5 heroes allowed in a game.")
    def addVillain(self, vil):
        # same as addHero() but for villains
        if len(self.villainDict) < 5:
            self.villainDict[vil.character.name] = vil
            self.villains.append(vil)
        else:
            print("No more than 5 villains allowed in a game.")
    def setEnvironment(self, e):
        self.environment = e
    def setupGame(self):
        # make sure that the game includes 3 to 5 heroes and either 1 villain, or the same number of villains as heroes (team villains)
        if len(self.heroes) < 1:
            print("At least 3 heroes required to play.")
        elif len(self.villains) != len(self.heroes):
            print("In a team villains game, you have to have the same number of heroes and villains.")
        else:
            # place each villain and hero alternately in the turn order, then the environment
            i = 0
            for h in self.heroes:
                if i < len(self.villains):
                    self.turnOrder.append(self.villains[i])
                    i += 1
                self.turnOrder.append(h)
            self.turnOrder.append(self.environment)
        ## do villain setup stuff; figure out how that's determined later
        for h in self.heroes:
            # set H for each card that uses it, then each hero draws 4 cards
            h.setH(len(self.heroes))
            h.draw(4)
        self.environment.setH(len(self.heroes))
    def actionHandler(self, source, card, actions, played=False):
        # actionHandler is the primary heavy lifter of the sim; since everything is broken down into types of actions,
        # they all go through this function
        # the source play area is given, the card the actions originate from is given, and the list of actions is given
        # the reason all three are separately needed is because some actions come from cards in play areas other than
        # their owners' (such as absolute zero's impale) and the actions happening aren't always exactly the list of
        # actions from the card (such as a card with multiple powers being played vs one of the powers being used)
        # played is used to indicate when it's a card played from their hand, for the purposes of discarding one-shots
        # (though really, it might just be that if the card is a one shot, it should get put in its trash after this
        # regardless, but there might be some weird case where that's not true, I dunno) (we'll see)
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
                            skp = int(input('enter 0 to draw {}, 1 to skip '.format(q[0])))
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
                # the card gets put into play based on the put's targeting
                # then, if there's an associated effect, the put target is used to setup that effect
                # and the effect has its own targeting to determine where to put it
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
                                print('a power:', pow)
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
