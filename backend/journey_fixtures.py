"""Explicit invented AI replies for the 25 Task 50A offline acceptance cases.

These are test data, never a production keyword interpreter or model fallback.
"""
from backend.ai import Interpretation

def reply(phrases, *, order=(), ordering=None, endpoint=None, total=None, deadline=None,
          optional=(), kinds=None, durations=None, clarification='', location=None,
          transport=None, dates=(), shared=None):
    stops=[]
    for i,p in enumerate(phrases):
        s={'source':p}
        if i in optional: s.update(requirement='optional',evidence=optional[i])
        if kinds and i in kinds: s['kind']=kinds[i]
        if durations and i in durations: s['duration']=durations[i]
        stops.append(s)
    return dict(activities=phrases, budget_per_person=None, date=None, location=location,
        preferences=[], date_expressions=list(dates), transport=transport,
        journey=dict(stops=stops, order=[dict(before=a,after=b,source=s) for a,b,s in order],
            ordering=ordering or ('constrained' if order else 'unspecified'),
            endpoint=endpoint, total_duration=total, deadline=deadline, clarification=clarification,shared_place=shared))

CASES = [
('Dinner and drinks in Jersey City tomorrow.', reply(['Dinner','drinks'],location='Jersey City',dates=['tomorrow']), 'simple'),
('Play a movie and get food afterward.', reply(['movie','food'],order=[(0,1,'movie and get food afterward')]), 'missing'),
('Go to SUNY College of Optometry.', reply(['SUNY College of Optometry'],kinds={0:'named_place'}), 'advanced'),
('Go to SUNY College of Optometry and then get coffee.', reply(['SUNY College of Optometry','coffee'],kinds={0:'named_place'},order=[(0,1,'SUNY College of Optometry and then get coffee')]), 'advanced'),
('Buy groceries and stop at an ATM.', reply(['groceries','ATM']), 'missing'),
('Buy groceries and maybe stop for coffee.', reply(['groceries','coffee'],optional={1:'maybe stop for coffee'}), 'advanced'),
('Go to the pharmacy first, then the supermarket.', reply(['pharmacy','supermarket'],order=[(0,1,'pharmacy first, then the supermarket')]), 'missing'),
('Visit the bank and grocery store, whichever is closer first.', reply(['bank','grocery store'],ordering='flexible'), 'advanced'),
('Go to the museum, then get coffee, then go home.', reply(['museum','coffee'],order=[(0,1,'museum, then get coffee')],endpoint={'kind':'home','source':'go home'}), 'clarify'),
('Go to the supermarket and return to where I started.', reply(['supermarket'],endpoint={'kind':'origin','source':'return to where I started'}), 'advanced'),
('Visit the college and finish at Penn Station.', reply(['college'],kinds={0:'named_place'},endpoint={'kind':'named_place','source':'finish at Penn Station'},clarification='the college'), 'clarify'),
('Get groceries and return home within 45 minutes.', reply(['groceries'],endpoint={'kind':'home','source':'return home'},total={'minutes':45,'relation':'maximum','source':'within 45 minutes'}), 'clarify'),
('Finish all errands in less than 30 minutes.', reply([],total={'minutes':30,'relation':'under','source':'less than 30 minutes'},clarification='errands'), 'clarify'),
('Be back home by 6 PM.', reply([],endpoint={'kind':'home','source':'back home'},deadline={'source':'by 6 PM'}), 'clarify'),
('Spend 20 minutes shopping and five minutes at an ATM.', reply(['shopping','ATM'],durations={0:{'minutes':20,'source':'20 minutes'},1:{'minutes':5,'source':'five minutes'}}), 'advanced'),
('Spend at least an hour at the museum.', reply(['museum'],durations={0:{'minutes':60,'relation':'minimum','source':'at least an hour'}}), 'advanced'),
('Visit Zara and Nike in the same mall.', reply(['Zara','Nike'],kinds={0:'brand',1:'brand'},shared={'stops':[0,1],'source':'same mall'}), 'advanced'),
('Only Zara outlets, then coffee.', reply(['Only Zara outlets','coffee'],kinds={0:'brand'},order=[(0,1,'Only Zara outlets, then coffee')]), 'missing'),
('Walk to a grocery store and return home.', reply(['grocery store'],transport='walking',endpoint={'kind':'home','source':'return home'}), 'clarify'),
('Drive to the bank, then walk to a café.', reply(['bank','café'],order=[(0,1,'Drive to the bank, then walk to a café')],clarification='Drive to the bank, then walk to a café'), 'clarify'),
('Visit the pharmacy before the bank, but the bank before the pharmacy.', reply(['pharmacy','bank'],clarification='pharmacy before the bank, but the bank before the pharmacy'), 'clarify'),
('Go to a coffee shop tomorrow afternoon.', reply(['coffee shop'],dates=['tomorrow afternoon']), 'missing'),
('Movie tomorrow in Hyderabad.', reply(['Movie'],location='Hyderabad',dates=['tomorrow']), 'simple'),
('Play soccer tomorrow in Jersey City.', reply(['soccer'],location='Jersey City',dates=['tomorrow']), 'simple'),
('Go somewhere nice tonight.', reply(['somewhere nice'],dates=['tonight']), 'missing'),
]

class FixtureAI:
    def interpret(self, text):
        for original, data, _ in CASES:
            if text == original:
                return Interpretation.model_validate(data)
        extra = {
            'Dinner and bowling tomorrow in Jersey City.': reply(['Dinner','bowling'],location='Jersey City',dates=['tomorrow']),
            'Get coffee in New York tomorrow and finish before 3 PM.': reply(['coffee'],location='New York',dates=['tomorrow'],deadline={'source':'before 3 PM','relation':'before'}),
            'Get groceries, use an ATM and return to where I started within 45 minutes.': reply(['groceries','ATM'],
                endpoint={'kind':'origin','source':'return to where I started'},
                total={'minutes':45,'relation':'maximum','source':'within 45 minutes'}),
            'Start at 2 PM, get coffee in New York tomorrow and finish before 3 PM.': reply(['coffee'],
                location='New York',dates=['tomorrow'],deadline={'source':'before 3 PM','relation':'before'}),
            'Go to SUNY College of Optometry then get coffee today.': reply(['SUNY College of Optometry','coffee'],kinds={0:'named_place'},dates=['today'],order=[(0,1,'SUNY College of Optometry then get coffee')]),
            'Go grocery shopping, then return home.': reply(['grocery shopping'],endpoint={'kind':'home','source':'return home'}),
            'Get groceries and return to where I started within 45 minutes.': reply(['groceries'],endpoint={'kind':'origin','source':'return to where I started'},total={'minutes':45,'relation':'maximum','source':'within 45 minutes'}),
            'Go to Penn Station today.': reply(['Penn Station'],kinds={0:'named_place'},dates=['today']),
            'Go to Fictional Missing College today.': reply(['Fictional Missing College'],kinds={0:'named_place'},dates=['today']),
            'Coffee and museum in Baltimore tomorrow.': reply(['Coffee','museum'],location='Baltimore',dates=['tomorrow']),
        }
        if text in extra: return Interpretation.model_validate(extra[text])
        # Deliberate browser revision example, still an explicit fixture.
        if text == 'Coffee in Baltimore tomorrow.':
            return Interpretation.model_validate(reply(['Coffee'],location='Baltimore',dates=['tomorrow']))
        raise ValueError('No offline fixture for this request')
