#!/usr/local/bin/perl -wT
# Translate webpages to the dialect spoken in Berlin, Germany
# NAVBAR muss noch eingebaut werden auch in slowdeath
use strict;

##### Package Berlinifyer start #####
package Berlinifyer;
use base "HTML::Parser";

use CGI qw(-no_xhtml);
use LWP::Simple;

# Security measurements
$CGI::POST_MAX=1024*100;  # max 100 KBytes posts
$CGI::DISABLE_UPLOADS = 1;  # no uploads
$ENV{'PATH'} = '/bin:/usr/bin';
delete @ENV{'IFS','CDPATH','ENV','BASH_ENV'};

# Get user input
my $q = new CGI;
my ($url,$base_url,$regex_url) = undef; # must be global to be used in tha package's methods
if ($q->param()) {
    $url = $q->param('url');
    unless (($url =~ m|^(http://[\w.\@/~,\?&%\+=-]+)$|i) && (length($url) > 11)) {
	slowdeath("<b>Der eingegebene URL '$url' wird von diesem Programm nich akzeptiert!</b>");
    }
    $url = $1; # untainted
    
    # Enable conversion of relative to full urls
    if ($url =~ m{^(.*/)\w+\.\w+\s*$}) {
	$base_url = $1;
    } elsif ($url =~ m{^(http://.*?)/?\s*$}) {
	$base_url = $1.'/'; # append / after hostname
    } else {
	slowdeath("<b>Der eingegebene URL '$url' wird von diesem Programm nich akzeptiert!</b>");
    }
    # Precompile RegEx to speed up program     
    $regex_url = qr($base_url);
}

my $berlinified = undef; # String, where CGI-output is saved
sub comment {
    my ($self, $comment) = @_;
    $berlinified .= "<!-- $comment -->";
}

sub start {
    my ($self, $tag, $attr, $attrseq, $origtext) = @_;
    # Expand relative to full url, ignore object tag
    # Does not yet work properly
    unless ($tag eq 'a' || $tag eq 'img' || $tag eq 'link') {
	$berlinified .= $origtext;
	return;
    }
    if (defined($attr->{'href'})) {
	if ($attr->{'href'} !~ /^\s*http|^\s*mailto|$regex_url/) {
	    $attr->{'href'} =~ s|^\s*(?:\.{0,2}/)*(.*)$|$base_url$1|;
	    $berlinified .= "<$tag ";
	    for(@$attrseq) {
		$berlinified .= $_ . qq(="$attr->{$_}" );
	    }
	    $berlinified .= ">";
	}
    } elsif (defined($attr->{'src'})) {
	if ($attr->{'src'} !~ /^\s*http|$regex_url/) {
	    $attr->{'src'} =~ s|^\s*(?:\.{0,2}/)*(.*)$|$base_url$1|;
	    $berlinified .= "<img ";
	    for(@$attrseq) {
		$berlinified .= $_ . qq(="$attr->{$_}" );
	    }
	    $berlinified .= ">";
	}
    }
}

sub text {
    my ($self, $text) = @_;
    $text = substitute($text);
    $berlinified .= $text;
}

sub end {
    my ($self, $tag, $origtext) = @_;
    $berlinified .= $origtext;
}
##### Package Berlinifyer end #####

##### Main program start #####
# Variables
my $rahoo_url = 'http://www.rahoo.de/';
my $css_url = $rahoo_url.'style/rahoostyle.css';
my $cgi_url = 'http://user.cs.tu-berlin.de/~ramiro/cgi-bin/berlinifyer.cgi';
my $outfile = undef;
my $vowel = 'aeiouäöü';

if ($q->param()) {
    my $p = new Berlinifyer;
    my $doc = get $url;
    $p->parse($doc);
    $p->eof(); # Clear buffer
    print $berlinified;
}
else {
    my $title = 'Rahoo - Berlinifyer';
    print $q->header(),$q->start_html({'title'=>$title,'author'=>'webmaster@rahoo.de','style'=>{'src'=>$css_url}});
    print $q->p('Hier k&ouml;nnen HTML-Dokumente ins Berlinische übersetzt werden. Bitte geben Sie die Internetadresse, des zu übersetzenden Dokuments an.'),
    $q->start_form({'method'=>'get'}),$q->textfield({'name'=>'url',
				    'size'=>'50',
				    'maxlength'=>'100',
				    'default'=>'http://'}),$q->submit(),
    $q->end_form(),$q->end_html();
}
##### Main program end #####

##### Subroutines start ######
# translate to Berlinisch
# NOT YET PERFECT !!!!!!!!!!!!!!!!
sub substitute {
    my $line = shift;
    my %subst_words = ('An der' => 'Anna',
		       'an der' => 'anna',
		       'An die' => 'Anne',
		       'an die' => 'anne',
		       'Auch' => 'Och',
		       'auch' => 'och',
		       'Auf' => 'Uff',
		       'auf' => 'uff',
		       'Du' => 'De',
		       'du' => 'de',
		       'Ich' => 'Ick',
		       'ich' => 'ick',
		       'In der' => 'Inna',
		       'in der' => 'inna',
		       'In die' => 'Inne',
		       'in die' => 'inne',
		       'Was' => 'Wat',
		       'was' => 'wat');

    for(keys %subst_words) {$line =~ s/(\b)$_(\b)/$1$subst_words{$_}$2/g;}
    $line =~ s^ei(\w)^ee$1^g;
    $line =~ s|(\w{2,})er([^$vowel])|$1a$2|g;
    $line =~ s|([$vowel])r([^$vowel])|$1a$2|g;
    $line =~ s|([^n])g([r$vowel])|$1j$2|g;
    $line =~ s/([^$vowel][^n])g(\b)/$1ch$2/g;
    return $line;
}

# Handle incorrect input
# NOT YET FINISHED
sub slowdeath {
    my $message = shift;
    my $title = 'Fehler';
    print $q->header(),
    $q->start_html(-title=>"$title",
		   -style=>{'src' =>$css_url}),
    $q->p($message), $q->end_html;
    exit(1);
}
__END__
