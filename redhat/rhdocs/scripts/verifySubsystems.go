package main

import (
	"io/ioutil"
	"log"
	"os"
	"strings"

	"gopkg.in/yaml.v2"
)

type NameAndEmail struct {
	Name string
	Email string
	Restricted bool
	Gluser string
}

type SubSystem struct {
	Subsystem string `subsystem`
	Labels struct {
		Name string `name`
		ReadyForMergeDeps []string `readyForMergeDeps`
		NewLabels string `newLabels`
		EmailLabel string `emailLabel`
	}
	Status string `status`
	Maintainers []NameAndEmail `maintainers`
	Reviewers []NameAndEmail `reviewers`
	Paths struct {
		Includes []string
		IncludeRegexes []string
		Excludes []string
	}
	Scm string `scm`
	MailingList string `mailingList`
}

type SubSystems struct {
	SubSys []SubSystem `subsystems`
}

func main() {
	var subSystems SubSystems

	filename := os.Args[1]
	source, err := ioutil.ReadFile(filename)
	if err != nil {
		panic(err)
	}

	err = yaml.Unmarshal(source, &subSystems)
	if err != nil {
		log.Fatalf("error: %v", err)
	}

	//
	// Check for duplicate Subsystem 'Label' entries
	//
	com := make(map[string]string)
	for _, s := range subSystems.SubSys {
		if _, ok := com[s.Labels.Name]; ok {
			if s.Labels.Name != "redhat" {
				log.Fatalf("error: Found duplicate Subsystem Label '%s' for entries '%s' and '%s'", s.Labels.Name, s.Subsystem, com[s.Labels.Name])
			}
		}
		com[s.Labels.Name] = s.Subsystem
	}

	//
	// check for machine-readable Alphabetical order
	//
	last := subSystems.SubSys[0]
	for count, s := range subSystems.SubSys {
		if count == 0 {
			continue
		}
		last = subSystems.SubSys[count-1]
		if strings.ToUpper(s.Subsystem) < strings.ToUpper(last.Subsystem) {
			if !strings.HasPrefix(last.Subsystem, "RHEL") {
				log.Fatalf("error: entries '%s' and '%s' are not in alphabetical order.\n", s.Subsystem, last.Subsystem)
			}
		}
	}

	// check that all names have a gluser entry
	for _, s := range subSystems.SubSys {
		for _, m := range s.Maintainers {
			if m.Gluser == "" {
				log.Fatalf("error: '%s' has maintainer %s <%s> listed without a gluser: entry", s.Subsystem, m.Name, m.Email)
			}
		}
		for _, r := range s.Reviewers {
			if r.Gluser == "" {
				log.Fatalf("error: '%s' has reviewer %s <%s> listed without a gluser: entry", s.Subsystem, r.Name, r.Email)
			}
		}
	}
}
