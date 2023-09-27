
from machine import Pin
import sys
from collections import OrderedDict
import uasyncio as asyncio
from machine import RTC
import ntptime

from delay_ms import Delay_ms
import ulogger

from config import SCENARIOS, PINS, SETTINGS

class Clock(ulogger.BaseClock):
    def __init__(self):
        self.rtc = RTC()
        ntptime.host = "ntp.ntsc.ac.cn"
        #ntptime.settime()

    def __call__(self) -> str:
        y,m,d,_,h,mi,s,_ = self.rtc.datetime ()
        return '%d-%d-%d %d:%d:%d' % (y,m,d,h,mi,s)
clock = Clock()

handlers = (
    ulogger.Handler(
        level=ulogger.INFO,
        colorful=True,
        fmt="&(time)% - &(level)% - &(name)% - &(fnname)% - &(msg)%",
        clock=clock,
        direction=ulogger.TO_TERM,
    ),
    ulogger.Handler(
        level=ulogger.ERROR,
        fmt="&(time)% - &(level)% - &(name)% - &(fnname)% - &(msg)%",
        clock=clock,
        direction=ulogger.TO_FILE,
        file_name="logging.log",
        max_file_size=2048 # max for 2k
    )
)

_LOGGER = ulogger.Logger(__name__, handlers)

class Condition(object):
    """ A helper class to call condition checks in the intended way.
    Attributes:
        func (str or callable): The function to call for the condition check
        target (bool): Indicates the target state--i.e., when True,
                the condition-checking callback should return True to pass,
                and when False, the callback should return False to pass.
    """

    def __init__(self, func, target=True):
        """
        Args:
            func (str or callable): Name of the condition-checking callable
            target (bool): Indicates the target state--i.e., when True,
                the condition-checking callback should return True to pass,
                and when False, the callback should return False to pass.
        Notes:
            This class should not be initialized or called from outside a
            Transition instance, and exists at module level (rather than
            nesting under the transition class) only because of a bug in
            dill that prevents serialization under Python 2.7.
        """
        self.func = func
        self.target = target

    def check(self, machine):
        """ Check whether the condition passes.
        """
        predicate = machine.resolve_callable(self.func)

        return predicate() == self.target

    def __repr__(self):
        return "<%s(%s)@%s>" % (type(self).__name__, self.func, id(self))


class Transition(object):
    """ Representation of a transition managed by a ``Machine`` instance.
    Attributes:
        source (str): Source state of the transition.
        dest (str): Destination state of the transition.
        prepare (list): Callbacks executed before conditions checks.
        conditions (list): Callbacks evaluated to determine if
            the transition should be executed.
        before (list): Callbacks executed before the transition is executed
            but only if condition checks have been successful.
        after (list): Callbacks executed after the transition is executed
            but only if condition checks have been successful.
    """

    condition_cls = Condition
    """ The class used to wrap condition checks. Can be replaced to alter condition resolution behaviour
        (e.g. OR instead of AND for 'conditions' or AND instead of OR for 'unless') """

    def __init__(self, model, conditions=None, unless=None, before=None,
                 after=None, prepare=None):
        """
        Args:
            source (str): The name of the source State.
            dest (str): The name of the destination State.
            conditions (optional[str, callable or list]): Condition(s) that must pass in order for
                the transition to take place. Either a string providing the
                name of a callable, or a list of callables. For the transition
                to occur, ALL callables must return True.
            unless (optional[str, callable or list]): Condition(s) that must return False in order
                for the transition to occur. Behaves just like conditions arg
                otherwise.
            before (optional[str, callable or list]): callbacks to trigger before the
                transition.
            after (optional[str, callable or list]): callbacks to trigger after the transition.
            prepare (optional[str, callable or list]): callbacks to trigger before conditions are checked
        """
        self.model = model
                     
        self.dest = None
                     
        self.prepare = [self._check_source_dest]
        self.before = [self._check_allowed_states]
        self.after = [self._remove_priority]
        
        self.add_callback('prepare', prepare)
        self.add_callback('before', before)
        self.add_callback('after', after)

        self.conditions = [self._check_model_priority]
        
        if conditions is not None:
            for cond in conditions:
                self.conditions.append(self.condition_cls(cond))
        if unless is not None:
            for cond in unless:
                self.conditions.append(self.condition_cls(cond, target=False))

    # def _eval_conditions(self, machine): #evaluates to false only when all conditions fail.
    # 	result = []

    #     for cond in self.conditions:
    #         if cond.check(machine):
    #         	result.append(True)
    #         else:
    #         	result.append(False)
             	
    #     return any(result)

    def _eval_conditions(self, machine):
        for cond in self.conditions:
            if not cond.check(machine):
                #_LOGGER.debug("%s Transition condition failed: %s() does not return %s. Transition halted.",machine.name, cond.func, cond.target)
                return False
        return True

    def execute(self, machine):
        """ Execute the transition.
        Args:
            machine: An instance of class StateMachine.
        Returns: boolean indicating whether the transition was
            successfully executed (True if successful, False if not).
        """

        if self.model.ordered_transition:
            self._ordered_transitions()
        _LOGGER.info("{} on {} Initiating transition from state {} to state {}...".format(
                      self.model.name, machine.name, self.model.state.name, self.dest))

        machine.callbacks(self.prepare)
        _LOGGER.debug("{} Executed callbacks before conditions.".format(self.model.name, machine.name))

        if not self._eval_conditions(machine):
            return False

        machine.callbacks(self.before)
        _LOGGER.debug("{} Executed callback before transition.".format(self.model.name, machine.name))

        if self.dest:  # if self.dest is None this is an internal transition with no actual state change
            self._change_state(machine)

        machine.callbacks(self.after)
        _LOGGER.debug("{} Executed callback after transition.".format(self.model.name, machine.name))
        return True

    def _change_state(self, machine):
        machine.go_to_state(self.model, self.dest)

    def _ordered_transitions(self):
        """ Add a set of transitions that move linearly from state to state.
        Args:
            states (list): A list of state names defining the order of the
                transitions. E.g., ['A', 'B', 'C'] will generate transitions
                for A --> B, B --> C, and C --> A (if loop is True). If states
                is None, all states in the current instance will be used.
            loop (boolean): Whether to add a transition from the last
                state to the first state.
            loop_includes_initial (boolean): If no initial state was defined in
                the machine, setting this to True will cause the _initial state
                placeholder to be included in the added transitions. This argument
                has no effect if the states argument is passed without the
                initial state included.
        """
        states = self.model.ordered_states
        current_state_name = self.model.state.name

        len_transitions = len(states)
        if len_transitions < 2:
            raise ValueError("Can't create ordered transitions on a Machine "
                             "with fewer than 2 states.")

        try:
            self.dest = states[states.index(current_state_name)+1]
        except IndexError:
            self.dest = states[0]
            
    def _check_source_dest(self):
	if self.model.state.name == self.dest:
            self.dest = None

    def _check_allowed_states(self):
        if not self.dest in self.model.states.keys():
            self.dest = None
            
    def _check_model_priority(self):
    	return self.model.priority == 0   	
    	
    # def _check_right_state(self):
    # 	return self.model.state.name == 'Green'
    	
    def _remove_priority(self):
        if self.model.state.name == 'Red':
    	    self.model.priority = None

    def add_callback(self, trigger, func):
        """ Add a new before, after, or prepare callback.
        Args:
            trigger (str): The type of triggering event. Must be one of
                'before', 'after' or 'prepare'.
            func (str or callable): The name of the callback function or a callable.
        """
        callback_list = getattr(self, trigger)
        callback_list.append(func)

    def __repr__(self):
        return "<%s('%s', '%s')@%s>" % (type(self).__name__,
                                        self.model.state.name, self.dest, id(self))

#abstract state base class
class State(object):

    def __init__(self):
        pass

    @property
    def name(self):
        return ''

    def enter(self, machine, model):
        _LOGGER.info("Entering state {}".format(model.state.name))

    def exit(self, machine, model):
        _LOGGER.info("Exiting state {}".format(model.state.name))

    def update(self, machine, model):
        pass

#state machine class
class StateMachine(object):

    name = 'Traffic Control System'

    get_ready_time = SETTINGS['get_ready_time']

    shared_times = []

    transition_cls = Transition

    transitions = []

    delay = Delay_ms()

    gpios = PINS['GPIO_POOL']

    def __init__(self):        
        self.models = OrderedDict()

        self.delay.callback(self._run_transitions, ())

        self.check_event_time = 0

        self._initialize_machine()

    def _initialize_machine(self):
        self._add_models()
        self._create_transition(self)

    def _add_models(self): #(self, lamp_location, number_of_bulbs=3, states=[], initial=None):
        for value in SCENARIOS.values():
            if isinstance(value, list):
                for val in value:
                    if val['status'] == 'On':
                        name = val['name']
                        self.models[name] = Lamps(val['name'], val['states'], val['initial'], val['bulbs'])
                        _LOGGER.info(f"Created model: {val['name']} with GPIO {self.models[name].gpios}")                       
                    else:
                        _LOGGER.info(f"Model: {val['name']} is off!")
            else:
                if value['status'] == 'On':
                        name = value['name']
                        self.models[name] = Lamps(value['name'], value['states'], val['initial'], value['bulbs'])
                        _LOGGER.info(f"Created model: {value['name']} with GPIO {self.models[name].gpios}")
                else:
                    _LOGGER.info(f"Model: {value['name']} is off!")

   
    @staticmethod
    def _add_states(model, states):# this method can only be called in the lamp models
        for state_name in states:
            model.states[state_name] = getattr(sys.modules[__name__], state_name)()

    @staticmethod
    def _add_pins(model, states, number_of_bulbs):
        for pin, state_name in enumerate(states[:number_of_bulbs]):
            #print(StateMachine.gpios[pin])
            model.gpios[state_name.split('_')[0]] = Pin(StateMachine.gpios[pin], Pin.OUT)
        del StateMachine.gpios[:number_of_bulbs]

    @classmethod
    def _create_transition(cls, self, conditions=None, unless=None, before=None, after=None, prepare=None):
        for model in self.models.values():
            cls.transitions.append(cls.transition_cls(model, conditions, unless, before, after, prepare))

    def _run_transitions(self):
        for transition in self.transitions:
            transition.execute(self)

    def go_to_state(self, model, state_name):
        if model.state:
            _LOGGER.debug('Exiting {}'.format(model.state.name))
            model.state.exit(self, model)
        model.state = model.states[state_name]
        _LOGGER.debug('Entering {}'.format(model.state.name))
        model.state.enter(self, model)

    async def update(self):
        #await asyncio.sleep_ms(self.check_event_time) #delay asking for new priority for at least previous wait time
        #pubsub comm protocol to get the direction with the highest priority and the minimum time before checking back for an event (self.check_event_time)(make it async)
        #set self.check_event_time
        for model in self.models:
            #model.priority = 0 if model.name ==  self.priority_model else None
            await asyncio.sleep_ms(0)
        #self._run_transitions() #event triggered transition

    def powerSaverMode(self):# enter the mode when the densities on all the paths are zero
        '''Kills all the lamps and go to sleep. It wakes up when the flow rate has passed a threshold'''
        pass
        
    def callbacks(self, funcs):
        """ Triggers a list of callbacks """
        for func in funcs:
            self.callback(func)
            _LOGGER.debug("{} Executed callback {}".format(self.name, func))

    def callback(self, func):
        """ Trigger a callback function with passed event_data parameters. In case func is a string,
            the callable will be resolved from the passed model in event_data. This function is not intended to
            be called directly but through state and transition callback definitions.
        Args:
            func (str or callable): The callback function.
                1. First, if the func is callable, just call it
                2. Second, we try to import string assuming it is a path to a func
                3. Fallback to a model attribute
            event_data (EventData): An EventData instance to pass to the
                callback (if event sending is enabled) or to extract arguments
                from (if event sending is disabled).
        """

        func = self.resolve_callable(func)
        func()


     @staticmethod
    def resolve_callable(func):
        """ Converts a model's property name, method name or a path to a callable into a callable.
            If func is not a string it will be returned unaltered.
        Args:
            func (str or callable): Property name, method name or a path to a callable
        Returns:
            callable function resolved from string or func
        """
        if isinstance(func, str):
                try:
                    module_name, func_name = func.rsplit('.', 1)
                    module = __import__(module_name.split('.')[0])
                    for submodule_name in module_name.split('.')[1:]:
                        module = getattr(module, submodule_name)
                    func = getattr(module, func_name)
                except (ImportError, AttributeError, ValueError):
                    raise AttributeError("Callable with name '%s' could neither be retrieved from the passed "
                                         "model nor imported from a module." % func)
        return func


class Red(State):
    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return 'Red'

    def enter(self, machine, model):
        State.enter(self, machine, model)
        for state_name in self.name.split('_'):
            model.putOnLamp(state_name)

    def exit(self, machine, model):
        State.exit(self, machine, model)
        for state_name in self.name.split('_'):
            model.putOffLamp(state_name)

    def update(self, machine):
        pass

class Green(State):
    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return 'Green'

    def enter(self, machine, model):
        State.enter(self, machine, model)
        for state_name in self.name.split('_'):
            model.putOnLamp(state_name)

    def exit(self, machine, model):
        State.exit(self, machine, model)
        for state_name in self.name.split('_'):
            model.putOffLamp(state_name)

    def update(self, machine):
        pass


class Yellow_Green(State):
    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return 'Yellow_Green'

    def enter(self, machine, model):
        State.enter(self, machine, model)

        machine.delay.trigger(machine.get_ready_time*1000)

        for state_name in self.name.split('_'):
            model.putOnLamp(state_name)

    def exit(self, machine, model):
        State.exit(self, machine, model)
        for state_name in self.name.split('_'):
            model.putOffLamp(state_name)

    def update(self, machine):
        pass


class Yellow_Red(State):
    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return 'Yellow_Red'

    def enter(self, machine, model):
        State.enter(self, machine, model)

        machine.delay.trigger(machine.get_ready_time*1000)

        for state_name in self.name.split('_'):
            model.putOnLamp(state_name)

    def exit(self, machine, model):
        State.exit(self, machine, model)
        for state_name in self.name.split('_'):
            model.putOffLamp(state_name)

    def update(self, machine):
        pass


class Lamps():

    def __init__(self, lamp_location, states, init_state='Dummy', number_of_bulbs=3):
                
        self.priority = None
        
        self.lamp_location = lamp_location
        self.name = lamp_location
        self.number_of_bulbs = number_of_bulbs

        self.ordered_states = states
        
        self.gpios = {}
        StateMachine._add_pins(self, states, number_of_bulbs)

        self.state = getattr(sys.modules[__name__], init_state)()
        self.states = {}
        StateMachine._add_states(self, states)

    def putOnLamp(self, state_name):
        print(f'put on {state_name} on pin {self.gpios[state_name]}')
        self.gpios[state_name].on()

    def putOffLamp(self, state_name):
        print(f'put off {state_name} on pin {self.gpios[state_name]}')
        self.gpios[state_name].off()

    def toggleLamp(self, state_name):
        pass #toggle the misc lamp between red and green states

    def flashLamp(self, state_name):
        pass #flashes only the yellow lamp at a certain rate


def set_global_exception():
    def handle_exception(loop, context):
        import sys
        sys.print_exception(context["exception"])
        sys.exit()
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)




# Create the state machine
fsm = StateMachine()


async def main():
    set_global_exception()
    while True:
        #print('in main...')
        await fsm.update()
        await asyncio.sleep(1)


try:
    asyncio.run(main())
except:
    fsm.delay.stop() #stop the timer
    asyncio.new_event_loop()  # Clear retained state
