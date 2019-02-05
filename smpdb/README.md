# Post-process SMPDB pathways

Script that updates a set of SMPDB pathways networks on http://www.ndexbio.org/#/networkset/00289894-2025-11e9-bb6a-0ac135e8bacf
(or any other place as specified by command line arguments).

Specifications are given here: https://ndexbio.atlassian.net/browse/NSU-78

## Running the script

python process_smpdb.py <username> <password> <ndex server> <network set uuid> <smpdb_pathways.csv file>

for example:

python process_smpdb.py ccc1 ccc2 dev.ndexbio.org 832e7ee6-24df-11e9-a05d-525400c25d22 smpdb_pathways.csv

After finishing, script gives a brief message with a number of network processed, for example:

Done. Processed 3 networks.

## Checking server response

Sc

## Prerequisites

What things you need to install the software and how to install them

```
Give examples
```

### Installing

A step by step series of examples that tell you how to get a development env running

Say what the step will be

```
Give the example
```

And repeat

```
until finished
```

End with an example of getting some data out of the system or using it for a little demo

## Running the tests

Explain how to run the automated tests for this system

### Break down into end to end tests

Explain what these tests test and why

```
Give an example
```

### And coding style tests

Explain what these tests test and why

```
Give an example
```

## Deployment

Add additional notes about how to deploy this on a live system

## Built With

* [Dropwizard](http://www.dropwizard.io/1.0.2/docs/) - The web framework used
* [Maven](https://maven.apache.org/) - Dependency Management
* [ROME](https://rometools.github.io/rome/) - Used to generate RSS Feeds

## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags). 

## Authors

* **Billie Thompson** - *Initial work* - [PurpleBooth](https://github.com/PurpleBooth)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Hat tip to anyone whose code was used
* Inspiration
* etc

