from collections import OrderedDict

SCENARIOS = OrderedDict([
            (
                1,
                    [
                        {
                            'name': 'North',
                            'bulbs': 3,
                            'states': ['Red', 'Yellow_Red', 'Green', 'Yellow_Green'],
                            'initial': 'Green',
                            'ordered_transition': True,
                            'status': 'On'
                        },

                        {
                            'name': 'South',
                            'bulbs': 3,
                            'states': ['Red', 'Yellow_Red', 'Green', 'Yellow_Green'],
                            'initial': 'Green',
                            'ordered_transition': True,
                            'status': 'On'
                        }
                    ]
            ),

            (
                2,

                    {
                        'name': 'Southx',
                        'bulbs': 2,
                        'states': ['Red', 'Green'],
                        'initial': 'Red',
                        'ordered_transition': True,
                        'status': 'On'
                    }


            ),

            (
                3,

                    {
                        'name': 'West',
                        'bulbs': 3,
                        'states': ['Red', 'Yellow_Red', 'Green', 'Yellow_Green'],
                        'initial': 'Red',
                        'ordered_transition': True,
                        'status': 'On'
                    }


            ),

            (
                4,

                    {
                        'name': 'East',
                        'bulbs': 3,
                        'states': ['Red', 'Yellow_Red', 'Green', 'Yellow_Green'],
                        'initial': 'Red',
                        'ordered_transition': True,
                        'status': 'Off'
                    }


            )

])

PINS = OrderedDict([
    (
        #"GPIO_POOL",
        #[0,2,3,4,5,12,13,14,15,18,19,21,22,23,25,26,27,32,33]# for esp32 38 pin config
        "GPIO_POOL",
        [13,14,12,27,33,26,15,4,18,23,22,25] #for esp32 30 pin config

    )


])

