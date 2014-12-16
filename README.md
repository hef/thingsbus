<A name="toc1-0" title="Things Bus Goals" />
# Things Bus Goals

* Offer a simple entry point to receive data from a variety of sources with minimal configuration (if any)
* Automatically create a directory of information based on the simplest of discovery configuration or inbound push-messages
* Enable distributed local-data-aware programming with a very shallow learning curve

<A name="toc1-7" title="Things Bus Architecture" />
# Things Bus Architecture

Based on ZeroMQ, Things Bus has 3 main parts:

* Pollers/Adaptors - bridges that are aware of both the thing they are tapping into, and Things Bus, so that the individual data sources don't have to be Things Bus aware
* Broker/Directory - Server system that looks at the information gathered by the pollers/adaptos, provides a point from which to receive it using one protocol, and generates a directory of the Things
* Consumers/Clients - Programs that are aware of Things Bus and may use helper libraries supplied by Things Bus, but aren't aware of the implementation details of the Things.



<A name="toc1-18" title="Examples" />
# Examples

<A name="toc2-21" title="Adapt lidless at PS1 to a broker" />
## Adapt lidless at PS1 to a broker

    python -m thingsbus.generic_zmq_adaptor --ns spacemon --nskey camname --tskey frame_time --filter mtype:percept_update --projections luminance,ratio_busy --url 'tcp://*:7955' -s tcp://bellamy.ps1:7202,tcp://bellamy.ps1:7200,tcp://bellamy.ps1:7201,tcp://bellamy.ps1:7206


Easy, right?

<A name="toc2-29" title="Run the broker" />
## Run the broker

    python -m thingsbus.broker


<A name="toc2-35" title="Use the adaptor module" />
## Use the adaptor module

    import thingsbus.adaptor
    adapt = thingsbus.adaptor.Adaptor('shop.shopbot', broker_input_url='tcp://*:7955')
    adapt.start()
    adapt.send({'busy': 12.0, 'light': 31.8}, ns='spacemon')

This sets up an adaptor that lets you send data under the `shop.shopbot` namespace, and then demonstrates sending data for the Thing `shop.shopbot.spacemon` that includes a busy percentage and a light percentage. If ts was supplied (float epoch) to the call to `send`, it would be passed through.



<A name="toc2-47" title="Connect to the broker and get data for a Thing" />
## Connect to the broker and get data for a Thing

	import thingsbus.client as client
	cl = client.Client(broker_url='tcp://*:7954')
	cl.start()
	sc = cl.directory.get_thing('shop.shopbot.spacemon')
	sc.get_data()

The lats call to `get_data` will return a tuple of float seconds (age of the data) and the data for the directory - if there is any data. If not, None will be returned.
