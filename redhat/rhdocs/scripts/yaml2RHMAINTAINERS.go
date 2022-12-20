package main

import (
	"fmt"
	"log"

	"gopkg.in/yaml.v2"
	"os"
	"io/ioutil"
)

type NameAndEmail struct {
	Name string
	Email string
	Restricted bool
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

func RHMAINTAINERS_header() {

	fmt.Printf("%s","\n")
	fmt.Printf("%s","	List of RHEL maintainers and how to submit kernel changes\n")
	fmt.Printf("%s","\n")
	fmt.Printf("%s","	OPTIONAL CC: the maintainers and mailing lists that are generated\n")
	fmt.Printf("%s","	by redhat/scripts/rh_get_maintainer.pl.	 The results returned by the\n")
	fmt.Printf("%s","	script will be best if you have git installed and are making\n")
	fmt.Printf("%s","	your changes in a branch derived from the latest RHEL git tree.\n")
	fmt.Printf("%s","\n")
	fmt.Printf("%s","Descriptions of section entries:\n")
	fmt.Printf("%s","\n")
	fmt.Printf("%s","	M: Maintainer of the subsystem (Name and email)\n")
	fmt.Printf("%s","	R: Reviewer of the subsystem (Name and email)\n")
	fmt.Printf("%s","	L: Mailing list that is relevant to this area\n")
	fmt.Printf("%s","	W: Web-page with status/info\n")
	fmt.Printf("%s","	T: SCM tree type and location.	Type is one of: git, hg, quilt, stgit.\n")
	fmt.Printf("%s","	S: Status, one of the following:\n")
	fmt.Printf("%s","	   Supported:	This feature is supported.\n")
	fmt.Printf("%s","	   Provided:	This feature is provided for a supported feature.\n")
	fmt.Printf("%s","	   Internal:	This feature is only provided for internal use.\n")
	fmt.Printf("%s","	F: Files and directories with wildcard patterns.\n")
	fmt.Printf("%s","	   A trailing slash includes all files and subdirectory files.\n")
	fmt.Printf("%s","	   F:	drivers/net/	all files in and below drivers/net\n")
	fmt.Printf("%s","	   F:	drivers/net/*	all files in drivers/net, but not below\n")
	fmt.Printf("%s","	   F:	*/net/*		all files in \"any top level directory\"/net\n")
	fmt.Printf("%s","	   One pattern per line.  Multiple F: lines acceptable.\n")
	fmt.Printf("%s","	X: Files and directories that are NOT maintained, same rules as F:\n")
	fmt.Printf("%s","	   Files exclusions are tested before file matches.\n")
	fmt.Printf("%s","	   Can be useful for excluding a specific subdirectory, for instance:\n")
	fmt.Printf("%s","	   F:	net/\n")
	fmt.Printf("%s","	   X:	net/ipv6/\n")
	fmt.Printf("%s","	   matches all files in and below net excluding net/ipv6/\n")
	fmt.Printf("%s","	N: Files and directories *Regex* patterns.\n")
	fmt.Printf("%s","	   N:	[^a-z]tegra	all files whose path contains tegra\n")
	fmt.Printf("%s","				(not including files like integrator)\n")
	fmt.Printf("%s","	   One pattern per line.  Multiple N: lines acceptable.\n")
	fmt.Printf("%s","	   scripts/get_maintainer.pl has different behavior for files that\n")
	fmt.Printf("%s","	   match F: pattern and matches of N: patterns.  By default,\n")
	fmt.Printf("%s","	   get_maintainer will not look at git log history when an F: pattern\n")
	fmt.Printf("%s","	   match occurs.  When an N: match occurs, git log history is used\n")
	fmt.Printf("%s","	   to also notify the people that have git commit signatures.\n")
	fmt.Printf("%s","	K: *Content regex* (perl extended) pattern match in a patch or file.\n")
	fmt.Printf("%s","	   For instance:\n")
	fmt.Printf("%s","	   K: of_get_profile\n")
	fmt.Printf("%s","	      matches patches or files that contain \"of_get_profile\"\n")
	fmt.Printf("%s","	   K: \\b(printk|pr_(info|err))\\b\n")
	fmt.Printf("%s","	      matches patches or files that contain one or more of the words\n")
	fmt.Printf("%s","	      printk, pr_info or pr_err\n")
	fmt.Printf("%s","	   One regex pattern per line.	Multiple K: lines acceptable.\n")
	fmt.Printf("%s","	I: Additional subject tag for rhkl patch submission.\n")
	fmt.Printf("%s","	P: Person (obsolete)\n")
	fmt.Printf("%s","\n")
	fmt.Printf("%s","Note: For the hard of thinking, this list is meant to remain in alphabetical\n")
	fmt.Printf("%s","order. If you could add yourselves to it in alphabetical order that would be\n")
	fmt.Printf("%s","so much easier [Ed]\n")
	fmt.Printf("%s","\n")
	fmt.Printf("%s","Red Hat Maintainers List (try to look for most precise areas first)\n")
	fmt.Printf("%s","\n")
	fmt.Printf("%s","		-----------------------------------\n")
	fmt.Printf("%s","\n")
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

	RHMAINTAINERS_header()

	for count, entry := range subSystems.SubSys {
		// Do not write disabled or unassigned entries into RHMAINTAINERS
		if entry.Status == "Disabled" || entry.Status == "Unassigned" {
			continue
		}

		if (count != 0) {
			fmt.Println("")
		}

		fmt.Println(entry.Subsystem)
		for _, name := range entry.Maintainers {
			fmt.Printf("M:\t%s <%s>\n", name.Name, name.Email)
		}
		for _, name := range entry.Reviewers {
			fmt.Printf("R:\t%s <%s>\n", name.Name, name.Email)
		}
		if entry.MailingList != "" {
			fmt.Printf("L:\t%s\n", entry.MailingList)
		}
		if entry.Status != "" {
			fmt.Printf("S:\t%s\n", entry.Status)
		}
		for _, file := range entry.Paths.Includes {
			fmt.Printf("F:\t%s\n", file)
		}
		for _, file := range entry.Paths.IncludeRegexes {
			fmt.Printf("N:\t%s\n", file)
		}
		for _, file := range entry.Paths.Excludes {
			fmt.Printf("X:\t%s\n", file)
		}
		if entry.Labels.EmailLabel != "" {
			fmt.Printf("I:\t%s\n", entry.Labels.EmailLabel)
		}
		if entry.Scm != "" {
			fmt.Printf("T:\t%s\n", entry.Scm)
		}
	}

}
