#!/usr/bin/perl -wT
# $Id: berlinifyer.cgi,v 1.14 2005/06/02 19:38:08 ramirogomez Exp $
#
# This cgi script translates web pages to
# the dialect spoken in Berlin, Germany.
#
# Copyright (C) 2002-2005 Ramiro Gómez 
# e-mail: web@ramiro.org
# url: www.ramiro.org
#
# This program is free software; you can redistribute it and/or
# modify it under the same terms as Perl itself.
use strict;

# If you need to specify additional paths to perl modules,
# do it here, e.g.:
# use lib qw(/home/pub/lib/perl5/site_perl/5.6.1);
use URI;
use CGI qw(-no_xhtml); # output HTML
use Carp;

# limit the size of posted data
$CGI::POST_MAX = 1024 * 100;

# disable CGI's upload function
$CGI::DISABLE_UPLOADS = 1;

# maximum size for a page to be berlinified 
use constant MAX_PAGE_SIZE => 1024 * 300;

# string where CGI-output is saved
my $berlinified = undef;

# new CGI object
my $q = CGI->new;

# prepend to links to berlinify the whole www
my $new_query = $q->script_name() . '?url='; 

# locale settings for pattern matching (ü,ö,ä)
use locale;
use POSIX 'locale_h';
setlocale(LC_CTYPE, 'de_DE') or croak "Invalid locale";

print $q->header();

if ($q->param()) {
    my $url = $q->param('url');
    unless ( ($url =~ m|^((?:[^:/?#]+:)?(?://[^/?#]*)?[^?#]*(?:\?[^#]*)?(?:#.*)?)| )  
			      && (length($url) > 11) ) {
	error("Der eingegebene URL '$url' wird 
von diesem Programm nicht akzeptiert!");
    }
    $url = $1; # untainted

    use HTML::Parser;
    my $p = HTML::Parser->new( api_version => 3,
			       start_h => [\&start, "self, tag, attr, attrseq, text"],
			       text_h => [ \&text, "self, dtext" ],
			       end_h   => [\&end, "self, tag, text"]
			       #comment_h => [""],
			       );
    # event handlers for HTML parser
    sub start {
	my ($self, $tag, $attr, $attrseq, $origtext) = @_;
	# Expand relative to full urls. Prepend $new_query to
	# webpage links, i.e. <a href="...">, so that linked pages
	# will be berlinified as well.
	# Applet and Object tags are currently ignored.
	
	# don't berlinify the contents of style tags
	if ($tag eq 'style') {
	    $self->{lasttag} = 1;
	    $berlinified .= $origtext;
	    return;
	}

	# handle scripts
	if ($tag eq 'script') {
	    if ( defined($attr->{'src'}) ) { # external
		$attr->{'src'} = URI->new_abs($attr->{'src'}, $p->{base});
		$berlinified .= "<$tag " . join (" ", map( $_ . qq(="$attr->{$_}"), @$attrseq)) . ">";
	    } else { # internal
		$self->{lasttag} = 1;
		$berlinified .= $origtext;
		return;
	    }
	} 
	
	# handle frames
	if ($tag eq 'frame') {
	    if (defined($attr->{'src'})) {
		$attr->{'src'} = $new_query . URI->new_abs($attr->{'src'}, $p->{base});
		$berlinified .= "<$tag " . join (" ", map( $_ . qq(="$attr->{$_}"), @$attrseq)) . ">";
		return;
	    }
	}

	# handle external style sheets
	if ($tag eq 'link') {
	    if (defined($attr->{'href'})) {
		$attr->{'href'} = URI->new_abs($attr->{'href'}, $p->{base});
		$berlinified .= "<$tag " . join (" ", map( $_ . qq(="$attr->{$_}"), @$attrseq)) . ">";
		return;
	    }
	}
	
	# handle links, images 
	if ($tag eq 'a' || $tag eq 'img' || $tag eq 'area') {
	    if ( defined($attr->{'href'}) && $attr->{'href'} !~ /^\s*mailto/ ) { # skip e-mail addresses
		$attr->{'href'} = $new_query . URI->new_abs($attr->{'href'}, $p->{base});		    
	    } elsif (defined($attr->{'src'})) {
		$attr->{'src'} = URI->new_abs($attr->{'src'}, $p->{base});
	    }
	    $berlinified .= "<$tag " . join (" ", map( $_ . qq(="$attr->{$_}"), @$attrseq)) . ">";
	    return;
	}
	
        # all other elements
	else {
	    $berlinified .= $origtext;
	    return;
	}
    } # sub start

    sub text {
	my ($self, $text) = @_;
	if (defined($self->{lasttag})) {
	    $berlinified .= $text;
	    return;
	}
	$berlinified .= substitute($text);
    }

    sub end {
	my ($self, $tag, $origtext) = @_;
	$berlinified .= $origtext;
	if ($tag =~ m/style|script/) {
	    $self->{lasttag} = undef;
	}
    }

    # get document and base url
    use LWP;
    my $ua = LWP::UserAgent->new();
    my $request = HTTP::Request->new(GET => $url);
    my $response = $ua->request($request);
    if ($response->is_success) {
	$p->{base} = $response->base;
	
	if ( length( $response->content > MAX_PAGE_SIZE ) ) {
	    error("Das Dokument '$url' wird aufgrund der 
Gr&ouml;&szlig;enbegrenzung nicht verarbeitet!");
	} else {
	    # parse HTML
	    $p->parse($response->content);
	    $p->eof();
	    print $berlinified;
	}
    } else { 
	error("Das Dokument '$url' konnte nicht heruntergeladen werden!"); 
    }
} # if ($q->param())

# print HTML form
else {
    my $title = 'Berlinifyer';
    print $q->start_html( {'title'=>$title,'author'=>'Ramiro G&oacute;mez'} );
    print $q->p('Hier k&ouml;nnen Web-Dokumente ins Berlinische &uuml;bersetzt werden. 
Geben Sie die Internetadresse des zu &uuml;bersetzenden HTML-Dokuments an.'),
    $q->start_form({'method'=>'get'}),$q->textfield({'name'=>'url',
				    'size'=>'50',
				    'maxlength'=>'100',
				    'default'=>'http://'}),$q->submit(),
    $q->end_form(),$q->end_html();
}

# translate to Berlin's dialect 
sub substitute {
    my $line = shift;
    my $vowel = 'aeiouäöü';
    #my $consonant = 'bcdfghjklmnpqrstvwxyz';
    
    # translate only the plural form of words, where 
    # grammatical gender of source and target differ 
    my %subst_words = ('An der' => 'Anna',
		       'an der' => 'anna',
		       'An die' => 'Anne',
		       'an die' => 'anne',
		       'Auch' => 'Och',
		       'auch' => 'och',
		       'Bäuche' => 'Plautzen',
		       'Babys' => 'Murkel',
		       'Babies' => 'Murkel',
		       'Beamten' => 'Stubenpisser',
		       'Beamter' => 'Stubenpisser',
		       'Beine' => 'Kackstelzen',
		       'Brüder' => 'Atzen',
		       'Du' => 'De',
		       'du' => 'de',
		       'Elektriker' => 'Strippenzieher',
		       'Finger' => 'Wichsgriffel',
		       'Flasche' => 'Pulle',
		       'Flaschen' => 'Pullen',
		       'Frau' => 'Butze',
		       'Frauen' => 'Butzen',
		       'Frisur' => 'Fettpeitsche',
		       'Füße' => 'Quanten',
		       'Gesellschaft' => 'Blase',
		       'Gesichter' => 'Fratzen',
		       'Hand' => 'Pfote',
		       'Hände' => 'Wichsgriffel',
		       'Haare' => 'Peden',
		       'Herzen' => 'Cognacpumpen',
		       'Hitze' => 'Affenhitze',
		       'Hund' => 'Köter',
		       'Hunde' => 'Köter',
		       'Ich' => 'Ick',
		       'ich' => 'ick',
		       'In der' => 'Inna',
		       'in der' => 'inna',
		       'In die' => 'Inne',
		       'in die' => 'inne',
		       'Kinder' => 'Ableger',
		       'Kleidung' => 'Klamotten',
		       'Kneipe' => 'Destille',
		       'Kneipen' => 'Destillen',
		       'Lokale' => 'Destillen',
		       'Nein' => 'Nee',
		       'nein' => 'nee',
		       'Nichts' => 'Nischt',
		       'nichts' => 'nischt',
		       'Münder' => 'Futtaluken',
		       'Mutter' => 'Olle',
		       'Parfum' => 'Eau de Mief',
		       'Polizei' => 'Polente',
		       'Polizist' => 'Bulle',
		       'Polizisten' => 'Bullen',
		       'Rollstuhl' => 'AOK-Choppa',
		       'Rollstühle' => 'AOK-Choppa',
		       'Schwester' => 'Atze',
		       'Schwestern' => 'Atzen',
		       'sehe' => 'glotze',
		       'siehst' => 'glotzt',
		       'sieht' => 'glotzt',
		       'sehen' => 'glotzen',
		       'seht' => 'glotzt',
		       'Vater' => 'Oller',
		       'Verwandtschaft' => 'Blase',
		       'Was' => 'Wat',
		       'was' => 'wat',
		       'Wirtshäuser' => 'Destillen',
		       'Zigarette' => 'Zippe',
		       'Zigaretten' => 'Zippen');

    # substitute all keys of %subst_words with the corresponding values
    map ($line =~ s/(\b)$_(\b)/$1$subst_words{$_}$2/g, keys %subst_words);
    
    $line =~ s|(\b)Auf|$1Uff|g;
    $line =~ s|(\b)auf|$1uff|g;
    $line =~ s|(\w{2,})er([^$vowel])|$1a$2|g;
    $line =~ s|([$vowel])r([^$vowel])|$1a$2|g;
    $line =~ s|([$vowel])hr(\b)|$1a$2|g;
    $line =~ s|([^n])g([r$vowel])|$1j$2|g;
    $line =~ s/([^$vowel][^n])g(\b)/$1ch$2/g;
    $line =~ s|(\b)g([^l])|$1j$2|g;
    $line =~ s|(\b)G([^l])|$1J$2|g;
    
    return $line;
}

# print error message
sub error {
    my $message = shift;
    print $q->start_html(-title=>"Fehler"),
    $q->p($message), $q->end_html();
    exit(1);
}
