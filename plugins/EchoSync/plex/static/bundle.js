//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1, t = !1;
function n() {
	t = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
n();
//#endregion
//#region node_modules/svelte/src/constants.js
var r = {}, i = Symbol("uninitialized"), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, _ = Object.isExtensible, v = () => {};
function ee(e) {
	return e();
}
function y(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function te() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var b = 1024, x = 2048, ne = 4096, re = 8192, ie = 16384, ae = 32768, oe = 1 << 25, se = 65536, S = 1 << 19, ce = 1 << 20, C = 65536, le = 1 << 21, ue = 1 << 22, de = 1 << 23, w = Symbol("$state"), fe = Symbol("legacy props"), pe = Symbol(""), me = Symbol("attributes"), he = Symbol("class"), ge = Symbol("style"), _e = Symbol("text"), ve = Symbol("form reset"), ye = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), be = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function xe(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function Se() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Ce(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function we() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Te(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Ee() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function De() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Oe(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function ke() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Ae() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function je() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Me() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Ne() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Pe(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Fe() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var T = !1;
function Ie(e) {
	T = e;
}
var E;
function D(e) {
	if (e === null) throw Pe(), r;
	return E = e;
}
function Le() {
	return D(/* @__PURE__ */ sn(E));
}
function O(e) {
	if (T) {
		if (/* @__PURE__ */ sn(E) !== null) throw Pe(), r;
		E = e;
	}
}
function Re(e = 1) {
	if (T) {
		for (var t = e, n = E; t--;) n = /* @__PURE__ */ sn(n);
		E = n;
	}
}
function ze(e = !0) {
	for (var t = 0, n = E;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ sn(n);
		e && n.remove(), n = i;
	}
}
function Be(e) {
	if (!e || e.nodeType !== 8) throw Pe(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Ve(e) {
	return e === this.v;
}
function He(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Ue(e) {
	return !He(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var k = null;
function We(e) {
	k = e;
}
function Ge(e, n = !1, r) {
	k = {
		p: k,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: G,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Ke(e) {
	var t = k, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) xn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, k = t.p, e ?? {};
}
function qe() {
	return !t || k !== null && k.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Je = [];
function Ye() {
	var e = Je;
	Je = [], y(e);
}
function Xe(e) {
	if (Je.length === 0 && !Ot) {
		var t = Je;
		queueMicrotask(() => {
			t === Je && Ye();
		});
	}
	Je.push(e);
}
function Ze() {
	for (; Je.length > 0;) Ye();
}
function Qe(e) {
	var t = G;
	if (t === null) return H.f |= de, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	$e(e, t);
}
function $e(e, t) {
	if (!(t !== null && t.f & 16384)) {
		for (; t !== null;) {
			if (t.f & 128) {
				if (!(t.f & 32768)) throw e;
				try {
					t.b.error(e);
					return;
				} catch (t) {
					e = t;
				}
			}
			t = t.parent;
		}
		throw e;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var et = ~(x | ne | b);
function A(e, t) {
	e.f = e.f & et | t;
}
function tt(e) {
	e.f & 512 || e.deps === null ? A(e, b) : A(e, ne);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function nt(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= C, nt(t.deps));
}
function rt(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), nt(e.deps), A(e, b);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var it = !1, at = !1;
function ot(e) {
	var t = at;
	try {
		return at = !1, [e(), at];
	} finally {
		at = t;
	}
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function st(e) {
	let t = 0, n = Kt(0), r;
	return () => {
		vn() && (Z(n), Dn(() => (t === 0 && (r = ar(() => e(() => Xt(n)))), t += 1, () => {
			Xe(() => {
				--t, t === 0 && (r?.(), r = void 0, Xt(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var ct = se | S;
function lt(e, t, n, r) {
	new ut(e, t, n, r);
}
var ut = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = T ? E : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = st(() => (this.#m = Kt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = kn(() => {
			if (T) {
				let e = this.#t;
				Le();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, ct), T && (this.#e = E);
	}
	#g() {
		try {
			this.#a = z(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = z(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = z(() => e(this.#e)), Xe(() => {
			var e = this.#c = document.createDocumentFragment(), t = an();
			e.append(t), this.#a = this.#x(() => z(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, Fn(this.#o, () => {
				this.#o = null;
			}), this.#b(j));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = z(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				zn(this.#a, e);
				let t = this.#n.pending;
				this.#o = z(() => t(this.#e));
			} else this.#b(j);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		rt(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = G, n = H, r = k;
		K(this.#i), W(this.#i), We(this.#i.ctx);
		try {
			return Pt.ensure(), e();
		} catch (e) {
			return Qe(e), null;
		} finally {
			K(t), W(n), We(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && Fn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, Xe(() => {
			this.#d = !1, this.#m && Jt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Z(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		j?.is_fork ? (this.#a && j.skip_effect(this.#a), this.#o && j.skip_effect(this.#o), this.#s && j.skip_effect(this.#s), j.oncommit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (B(this.#a), null), this.#o &&= (B(this.#o), null), this.#s &&= (B(this.#s), null), T && (D(this.#t), Re(), D(ze()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Fe();
				return;
			}
			r = !0, i && Me(), this.#s !== null && Fn(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				$e(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return z(() => {
						var t = G;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return $e(e, this.#i.parent), null;
				}
			}));
		};
		Xe(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				$e(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => $e(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function dt(e, t, n, r) {
	let i = qe() ? ht : vt;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = G, c = ft(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				$e(e, s);
			}
			pt();
		}
	}
	var d = mt();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ _t(e))).then(u).catch((e) => $e(e, s)).finally(d);
	}
	l ? l.then(() => {
		c(), f(), pt();
	}) : f();
}
function ft() {
	var e = G, t = H, n = k, r = j;
	return function(i = !0) {
		K(e), W(t), We(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function pt(e = !0) {
	K(null), W(null), We(null), e && j?.deactivate();
}
function mt() {
	var e = G, t = e.b, n = j, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function ht(e) {
	var t = 2 | x;
	return G !== null && (G.f |= S), {
		ctx: k,
		deps: null,
		effects: null,
		equals: Ve,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: G,
		ac: null
	};
}
var gt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function _t(e, t, n) {
	let r = G;
	r === null && Se();
	var a = void 0, o = Kt(i), s = !H, c = /* @__PURE__ */ new Set();
	return En(() => {
		var t = G, n = te();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== ye && n.reject(e);
			}).finally(pt);
		} catch (e) {
			n.reject(e), pt();
		}
		var i = j;
		if (s) {
			if (t.f & 32768) var l = mt();
			if (r.b?.is_rendered()) i.async_deriveds.get(t)?.reject(gt);
			else for (let e of c.values()) e.reject(gt);
			c.add(n), i.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== gt && (i.activate(), t ? (o.f |= de, Jt(o, t)) : (o.f & 8388608 && (o.f ^= de), Jt(o, e)), i.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), yn(() => {
		for (let e of c) e.reject(gt);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/*#__NO_SIDE_EFFECTS__*/
function vt(e) {
	let t = /* @__PURE__ */ ht(e);
	return t.equals = Ue, t;
}
function yt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) B(t[n]);
	}
}
function bt(e) {
	var t, n = G, r = e.parent;
	if (!V && r !== null && e.v !== i && r.f & 24576) return Ne(), e.v;
	K(r);
	try {
		e.f &= ~C, yt(e), t = Qn(e);
	} finally {
		K(n);
	}
	return t;
}
function xt(e) {
	var t = bt(e);
	if (!e.equals(t) && (e.wv = Yn(), (!j?.is_fork || e.deps === null) && (j === null ? e.v = t : (j.capture(e, t, !0), Et?.capture(e, t, !0)), e.deps === null))) {
		A(e, b);
		return;
	}
	V || (M === null ? tt(e) : (vn() || j?.is_fork) && M.set(e, t));
}
function St(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(ye), t.fn !== null && (t.teardown = v), t.ac = null, er(t, 0), jn(t));
}
function Ct(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && tr(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var wt = null, Tt = null, j = null, Et = null, M = null, Dt = null, Ot = !1, kt = !1, At = null, jt = null, Mt = 0, Nt = 1, Pt = class t {
	id = Nt++;
	#e = !1;
	linked = !0;
	#t = null;
	#n = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = /* @__PURE__ */ new Set();
	#a = 0;
	#o = /* @__PURE__ */ new Map();
	#s = null;
	#c = [];
	#l = [];
	#u = /* @__PURE__ */ new Set();
	#d = /* @__PURE__ */ new Set();
	#f = /* @__PURE__ */ new Map();
	#p = /* @__PURE__ */ new Set();
	is_fork = !1;
	#m = !1;
	constructor() {
		Tt === null ? wt = Tt = this : (Tt.#n = this, this.#t = Tt), Tt = this;
	}
	#h() {
		if (this.is_fork) return !0;
		for (let n of this.#o.keys()) {
			for (var e = n, t = !1; e.parent !== null;) {
				if (this.#f.has(e)) {
					t = !0;
					break;
				}
				e = e.parent;
			}
			if (!t) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#f.has(e) || this.#f.set(e, {
			d: [],
			m: []
		}), this.#p.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#f.get(e);
		if (n) {
			this.#f.delete(e);
			for (var r of n.d) A(r, x), t(r);
			for (r of n.m) A(r, ne), t(r);
		}
		this.#p.add(e);
	}
	#g() {
		this.#e = !0, Mt++ > 1e3 && (this.#S(), It());
		for (let e of this.#u) this.#d.delete(e), A(e, x), this.schedule(e);
		for (let e of this.#d) A(e, ne), this.schedule(e);
		let n = this.#c;
		this.#c = [], this.apply();
		var r = At = [], i = [], a = jt = [];
		for (let e of n) try {
			this.#_(e, r, i);
		} catch (t) {
			throw Ht(e), this.#h() || this.discard(), t;
		}
		if (j = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (At = null, jt = null, this.#h()) {
			this.#b(i), this.#b(r);
			for (let [e, t] of this.#f) Vt(e, t);
			a.length > 0 && j.#g();
			return;
		}
		let s = this.#v();
		if (s) {
			this.#b(i), this.#b(r), s.#y(this);
			return;
		}
		this.#u.clear(), this.#d.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), Et = this, Lt(i), Lt(r), Et = null, this.#s?.resolve();
		var c = j;
		if (this.#a === 0 && (this.#c.length === 0 || c !== null) && (this.#S(), e && (this.#x(), j = c)), this.#c.length > 0) if (c !== null) {
			let e = c;
			e.#c.push(...this.#c.filter((t) => !e.#c.includes(t)));
		} else c = this;
		c !== null && c.#g();
	}
	#_(t, n, r) {
		t.f ^= b;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#f.has(i)) && i.fn !== null) {
				o ? i.f ^= b : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : Xn(i) && (a & 16 && this.#d.add(i), tr(i));
				var s = i.first;
				if (s !== null) {
					i = s;
					continue;
				}
			}
			for (; i !== null;) {
				var c = i.next;
				if (c !== null) {
					i = c;
					break;
				}
				i = i.parent;
			}
		}
	}
	#v() {
		for (var e = this.#t; e !== null;) {
			if (!e.is_fork) {
				for (let [t, [, n]] of this.current) if (e.current.has(t) && !n) return e;
			}
			e = e.#t;
		}
		return null;
	}
	#y(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve).catch(e.reject);
		}
		e.async_deriveds.clear(), this.transfer_effects(e.#u, e.#d);
		let t = (e) => {
			var n = e.reactions;
			if (n !== null) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#d.delete(i), A(i, x), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#S(), j = this, this.#g();
	}
	#b(e) {
		for (var t = 0; t < e.length; t += 1) rt(e[t], this.#u, this.#d);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), M?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		j = this;
	}
	deactivate() {
		j = null, M = null;
	}
	flush() {
		try {
			kt = !0, j = this, this.#g();
		} finally {
			Mt = 0, Dt = null, At = null, jt = null, kt = !1, j = null, M = null, Wt.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear();
		for (let e of this.async_deriveds.values()) e.reject(gt);
		this.#S(), this.#s?.resolve();
	}
	register_created_effect(e) {
		this.#l.push(e);
	}
	#x() {
		for (let u = wt; u !== null; u = u.#n) {
			var e = u.id < this.id, t = [];
			for (let [r, [i, a]] of this.current) {
				if (u.current.has(r)) {
					var n = u.current.get(r)[0];
					if (e && i !== n) u.current.set(r, [i, a]);
					else continue;
				}
				t.push(r);
			}
			if (e) for (let [e, t] of this.async_deriveds) {
				let n = u.async_deriveds.get(e);
				n && t.promise.then(n.resolve).catch(n.reject);
			}
			var r = [...u.current.keys()].filter((e) => !u.current.get(e)[1]);
			if (!(!u.#e || r.length === 0)) {
				var i = r.filter((e) => !this.current.has(e));
				if (i.length === 0) e && u.discard();
				else if (t.length > 0) {
					if (e) for (let e of this.#p) u.unskip_effect(e, (e) => {
						e.f & 4194320 ? u.schedule(e) : u.#b([e]);
					});
					u.activate();
					var a = /* @__PURE__ */ new Set(), o = /* @__PURE__ */ new Map();
					for (var s of t) Rt(s, i, a, o);
					o = /* @__PURE__ */ new Map();
					var c = [...u.current].filter(([e, t]) => {
						let n = this.current.get(e);
						return n ? n[0] !== t[0] || n[1] !== t[1] : !0;
					}).map(([e]) => e);
					if (c.length > 0) for (let e of this.#l) !(e.f & 155648) && zt(e, c, o) && (e.f & 4194320 ? (A(e, x), u.schedule(e)) : u.#u.add(e));
					if (u.#c.length > 0 && !u.#m) {
						u.apply();
						for (var l of u.#c) u.#_(l, [], []);
						u.#c = [];
					}
					u.deactivate();
				}
			}
		}
	}
	increment(e, t) {
		if (this.#a += 1, e) {
			let e = this.#o.get(t) ?? 0;
			this.#o.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#a, e) {
			let e = this.#o.get(t) ?? 0;
			e === 1 ? this.#o.delete(t) : this.#o.set(t, e - 1);
		}
		this.#m || (this.#m = !0, Xe(() => {
			this.#m = !1, this.linked && this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#u.add(t);
		for (let e of t) this.#d.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#r.add(e);
	}
	ondiscard(e) {
		this.#i.add(e);
	}
	settled() {
		return (this.#s ??= te()).promise;
	}
	static ensure() {
		if (j === null) {
			let e = j = new t();
			!kt && !Ot && Xe(() => {
				e.#e || e.flush();
			});
		}
		return j;
	}
	apply() {
		if (!e || !this.is_fork && this.#t === null && this.#n === null) {
			M = null;
			return;
		}
		M = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) M.set(e, t);
		for (let e = wt; e !== null; e = e.#n) if (!(e === this || e.is_fork)) {
			var t = !1;
			if (e.id < this.id) {
				for (let [n, [, r]] of e.current) if (!r && this.current.has(n)) {
					t = !0;
					break;
				}
			}
			if (!t) for (let [t, n] of e.previous) M.has(t) || M.set(t, n);
		}
	}
	schedule(t) {
		if (Dt = t, t.b?.is_pending && t.f & 16777228 && !(t.f & 32768)) {
			t.b.defer_effect(t);
			return;
		}
		for (var n = t; n.parent !== null;) {
			n = n.parent;
			var r = n.f;
			if (At !== null && n === G && (e || (H === null || !(H.f & 2)) && !it)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= b;
			}
		}
		this.#c.push(n);
	}
	#S() {
		if (this.linked) {
			var e = this.#t, t = this.#n;
			e === null ? wt = t : e.#n = t, t === null ? Tt = e : t.#t = e, this.linked = !1;
		}
	}
};
function Ft(e) {
	var t = Ot;
	Ot = !0;
	try {
		var n;
		for (e && (j !== null && !j.is_fork && j.flush(), n = e());;) {
			if (Ze(), j === null) return n;
			j.flush();
		}
	} finally {
		Ot = t;
	}
}
function It() {
	try {
		Ee();
	} catch (e) {
		$e(e, Dt);
	}
}
var N = null;
function Lt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && Xn(r) && (N = /* @__PURE__ */ new Set(), tr(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && Pn(r), N?.size > 0)) {
				Wt.clear();
				for (let e of N) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) N.has(n) && (N.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || tr(n);
					}
				}
				N.clear();
			}
		}
		N = null;
	}
}
function Rt(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? Rt(i, t, n, r) : e & 4194320 && !(e & 2048) && zt(i, t, r) && (A(i, x), Bt(i));
	}
}
function zt(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && zt(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function Bt(e) {
	j.schedule(e);
}
function Vt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), A(e, b);
		for (var n = e.first; n !== null;) Vt(n, t), n = n.next;
	}
}
function Ht(e) {
	A(e, b);
	for (var t = e.first; t !== null;) Ht(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Ut = /* @__PURE__ */ new Set(), Wt = /* @__PURE__ */ new Map(), Gt = !1;
function Kt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Ve,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function qt(e, t) {
	let n = Kt(e, t);
	return Un(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function P(e, n = !1, r = !0) {
	let i = Kt(e);
	return n || (i.equals = Ue), t && r && k !== null && k.l !== null && (k.l.s ??= []).push(i), i;
}
function F(e, t, n = !1) {
	return H !== null && (!U || H.f & 131072) && qe() && H.f & 4325394 && (q === null || !q.has(e)) && je(), Jt(e, n ? Qt(t) : t, jt);
}
function Jt(e, t, n = null) {
	if (!e.equals(t)) {
		Wt.set(e, V ? t : e.v);
		var r = Pt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && bt(t), M === null && tt(t);
		}
		e.wv = Yn(), Zt(e, x, n), qe() && G !== null && G.f & 1024 && !(G.f & 96) && (X === null ? Wn([e]) : X.push(e)), !r.is_fork && Ut.size > 0 && !Gt && Yt();
	}
	return t;
}
function Yt() {
	Gt = !1;
	for (let e of Ut) {
		e.f & 1024 && A(e, ne);
		let t;
		try {
			t = Xn(e);
		} catch {
			t = !0;
		}
		t && tr(e);
	}
	Ut.clear();
}
function Xt(e) {
	F(e, e.v + 1);
}
function Zt(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = qe(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === G)) {
			var l = (c & x) === 0;
			if (l && A(s, t), c & 131072) Ut.add(s);
			else if (c & 2) {
				var u = s;
				M?.delete(u), c & 65536 || (c & 512 && (G === null || !(G.f & 2097152)) && (s.f |= C), Zt(u, ne, n));
			} else if (l) {
				var d = s;
				c & 16 && N !== null && N.add(d), n === null ? Bt(d) : n.push(d);
			}
		}
	}
}
function Qt(e) {
	if (typeof e != "object" || !e || w in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ qt(0), s = null, c = qn, l = (e) => {
		if (qn === c) return e();
		var t = H, n = qn;
		W(null), Jn(c);
		var r = e();
		return W(t), Jn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ qt(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && ke();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ qt(r.value, s);
				return n.set(t, e), e;
			}) : F(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ qt(i, s));
					n.set(t, e), Xt(a);
				}
			} else F(r, i), Xt(a);
			return !0;
		},
		get(t, r, a) {
			if (r === w) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ qt(Qt(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
				var u = Z(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = Z(a));
			} else if (r === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== i) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === w) return !0;
			var r = n.get(t), a = r !== void 0 && r.v !== i || Reflect.has(e, t);
			return (r !== void 0 || G !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ qt(a ? Qt(e[t]) : i, s)), n.set(t, r)), Z(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ qt(i, s)), n.set(p + "", m)) : F(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ qt(void 0, s)), F(u, Qt(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => Qt(o));
				F(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && F(_, v + 1);
				}
				Xt(a);
			}
			return !0;
		},
		ownKeys(e) {
			Z(a);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== i;
			});
			for (var [r, o] of n) o.v !== i && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			Ae();
		}
	});
}
new Set([
	"copyWithin",
	"fill",
	"pop",
	"push",
	"reverse",
	"shift",
	"sort",
	"splice",
	"unshift"
]);
var $t, en, tn, nn;
function rn() {
	if ($t === void 0) {
		$t = window, en = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		tn = f(t, "firstChild").get, nn = f(t, "nextSibling").get, _(e) && (e[he] = void 0, e[me] = null, e[ge] = void 0, e.__e = void 0), _(n) && (n[_e] = void 0);
	}
}
function an(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function on(e) {
	return tn.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function sn(e) {
	return nn.call(e);
}
function I(e, t) {
	if (!T) return /* @__PURE__ */ on(e);
	var n = /* @__PURE__ */ on(E);
	if (n === null) n = E.appendChild(an());
	else if (t && n.nodeType !== 3) {
		var r = an();
		return n?.before(r), D(r), r;
	}
	return t && dn(n), D(n), n;
}
function L(e, t = 1, n = !1) {
	let r = T ? E : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ sn(r);
	if (!T) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = an();
			return r === null ? i?.after(a) : r.before(a), D(a), a;
		}
		dn(r);
	}
	return D(r), r;
}
function cn(e) {
	e.textContent = "";
}
function ln() {
	return !e || N !== null ? !1 : (G.f & ae) !== 0;
}
function un(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function dn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var fn = !1;
function pn() {
	fn || (fn = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ve]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function mn(e) {
	var t = H, n = G;
	W(null), K(null);
	try {
		return e();
	} finally {
		W(t), K(n);
	}
}
function hn(e, t, n, r = n) {
	e.addEventListener(t, () => mn(n));
	let i = e[ve];
	i ? e[ve] = () => {
		i(), r(!0);
	} : e[ve] = () => r(!0), pn();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function gn(e) {
	G === null && (H === null && Te(e), we()), V && Ce(e);
}
function _n(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function R(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= re);
	var r = {
		ctx: k,
		deps: null,
		nodes: null,
		f: e | x | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	j?.register_created_effect(r);
	var i = r;
	if (e & 4) At === null ? Pt.ensure().schedule(r) : At.push(r);
	else if (t !== null) {
		try {
			tr(r);
		} catch (e) {
			throw B(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= se));
	}
	if (i !== null && (i.parent = n, n !== null && _n(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function vn() {
	return H !== null && !U;
}
function yn(e) {
	let t = R(8, null);
	return A(t, b), t.teardown = e, t;
}
function bn(e) {
	gn("$effect");
	var t = G.f;
	if (!H && t & 32 && k !== null && !k.i) {
		var n = k;
		(n.e ??= []).push(e);
	} else return xn(e);
}
function xn(e) {
	return R(4 | ce, e);
}
function Sn(e) {
	return gn("$effect.pre"), R(8 | ce, e);
}
function Cn(e) {
	Pt.ensure();
	let t = R(64 | S, e);
	return () => {
		B(t);
	};
}
function wn(e) {
	Pt.ensure();
	let t = R(64 | S, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Fn(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function Tn(e) {
	return R(4, e);
}
function En(e) {
	return R(ue | S, e);
}
function Dn(e, t = 0) {
	return R(8 | t, e);
}
function On(e, t = [], n = [], r = []) {
	dt(r, t, n, (t) => {
		R(8, () => {
			e(...t.map(Z));
		});
	});
}
function kn(e, t = 0) {
	return R(16 | t, e);
}
function z(e) {
	return R(32 | S, e);
}
function An(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = V, n = H;
		Hn(!0), W(null);
		try {
			t.call(null);
		} finally {
			Hn(e), W(n);
		}
	}
}
function jn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && mn(() => {
			e.abort(ye);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function Mn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Nn(e.nodes.start, e.nodes.end), n = !0), e.f |= oe, jn(e, t && !n), er(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	An(e), e.f ^= oe, e.f |= ie;
	var i = e.parent;
	i !== null && i.first !== null && Pn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Nn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ sn(e);
		e.remove(), e = n;
	}
}
function Pn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Fn(e, t, n = !0) {
	var r = [];
	In(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function In(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= re;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				In(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Ln(e) {
	Rn(e, !0);
}
function Rn(e, t) {
	if (e.f & 8192) {
		e.f ^= re, e.f & 1024 || (A(e, x), Pt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Rn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function zn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ sn(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Bn = null, Vn = !1, V = !1;
function Hn(e) {
	V = e;
}
var H = null, U = !1;
function W(e) {
	H = e;
}
var G = null;
function K(e) {
	G = e;
}
var q = null;
function Un(t) {
	H !== null && (!e || H.f & 2) && (q ??= /* @__PURE__ */ new Set()).add(t);
}
var J = null, Y = 0, X = null;
function Wn(e) {
	X = e;
}
var Gn = 1, Kn = 0, qn = Kn;
function Jn(e) {
	qn = e;
}
function Yn() {
	return ++Gn;
}
function Xn(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~C), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (Xn(a) && xt(a), a.wv > e.wv) return !0;
		}
		t & 512 && M === null && A(e, b);
	}
	return !1;
}
function Zn(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && q !== null && q.has(t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? Zn(o, n, !1) : n === o && (r ? A(o, x) : o.f & 1024 && A(o, ne), Bt(o));
	}
}
function Qn(e) {
	var t = J, n = Y, r = X, i = H, a = q, o = k, s = U, c = qn, l = e.f;
	J = null, Y = 0, X = null, H = l & 96 ? null : e, q = null, We(e.ctx), U = !1, qn = ++Kn, e.ac !== null && (mn(() => {
		e.ac.abort(ye);
	}), e.ac = null);
	try {
		e.f |= le;
		var u = e.fn, d = u();
		e.f |= ae;
		var f = e.deps, p = j?.is_fork;
		if (J !== null) {
			var m;
			if (p || er(e, Y), f !== null && Y > 0) for (f.length = Y + J.length, m = 0; m < J.length; m++) f[Y + m] = J[m];
			else e.deps = f = J;
			if (vn() && e.f & 512) for (m = Y; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && Y < f.length && (er(e, Y), f.length = Y);
		if (qe() && X !== null && !U && f !== null && !(e.f & 6146)) for (m = 0; m < X.length; m++) Zn(X[m], e);
		if (i !== null && i !== e) {
			if (Kn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Kn;
			if (t !== null) for (let e of t) e.rv = Kn;
			X !== null && (r === null ? r = X : r.push(...X));
		}
		return e.f & 8388608 && (e.f ^= de), d;
	} catch (e) {
		return Qe(e);
	} finally {
		e.f ^= le, J = t, Y = n, X = r, H = i, q = a, We(o), U = s, qn = c;
	}
}
function $n(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (J === null || !c.call(J, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~C), o.v !== i && tt(o), St(o), er(o, 0);
	}
}
function er(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) $n(e, n[r]);
}
function tr(e) {
	var t = e.f;
	if (!(t & 16384)) {
		A(e, b);
		var n = G, r = Vn;
		G = e, Vn = !0;
		try {
			t & 16777232 ? Mn(e) : jn(e), An(e);
			var i = Qn(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Gn;
		} finally {
			Vn = r, G = n;
		}
	}
}
async function nr() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), Ft();
}
function Z(e) {
	var t = (e.f & 2) != 0;
	if (Bn?.add(e), H !== null && !U && !(G !== null && G.f & 16384) && (q === null || !q.has(e))) {
		var n = H.deps;
		if (H.f & 2097152) e.rv < Kn && (e.rv = Kn, J === null && n !== null && n[Y] === e ? Y++ : J === null ? J = [e] : J.push(e));
		else {
			H.deps ??= [], c.call(H.deps, e) || H.deps.push(e);
			var r = e.reactions;
			r === null ? e.reactions = [H] : c.call(r, H) || r.push(H);
		}
	}
	if (V && Wt.has(e)) return Wt.get(e);
	if (t) {
		var i = e;
		if (V) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || ir(i)) && (a = bt(i)), Wt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !U && H !== null && (Vn || (H.f & 512) != 0), s = (i.f & ae) === 0;
		Xn(i) && (o && (i.f |= 512), xt(i)), o && !s && (Ct(i), rr(i));
	}
	if (M?.has(e)) return M.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function rr(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Ct(t), rr(t));
}
function ir(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (Wt.has(t) || t.f & 2 && ir(t)) return !0;
	return !1;
}
function ar(e) {
	var t = U;
	try {
		return U = !0, e();
	} finally {
		U = t;
	}
}
function or(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (w in e) sr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && w in n && sr(n);
		}
	}
}
function sr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			sr(e[n], t);
		} catch {}
		let n = g(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = p(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var cr = Symbol("events"), lr = /* @__PURE__ */ new Set(), ur = /* @__PURE__ */ new Set();
function dr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || mr.call(t, e), !e.cancelBubble) return mn(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? Xe(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function fr(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = dr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && yn(() => {
		t.removeEventListener(e, o, a);
	});
}
var pr = null;
function mr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	pr = e;
	var o = 0, s = pr === e && e[cr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[cr] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		d(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var u = H, f = G;
		W(null), K(null);
		try {
			for (var p, m = []; a !== null && a !== t;) {
				try {
					var h = a[cr]?.[r];
					h != null && (!a.disabled || e.target === a) && h.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble) break;
				o++, a = o < i.length ? i[o] : null;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[cr] = t, delete e.currentTarget, W(u), K(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var hr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function gr(e) {
	return hr?.createHTML(e) ?? e;
}
function _r(e) {
	var t = un("template");
	return t.innerHTML = gr(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function vr(e, t) {
	var n = G;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Q(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (T) return vr(E, null), E;
		i === void 0 && (i = _r(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ on(i)));
		var t = r || en ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ on(t), s = t.lastChild;
			vr(o, s);
		} else vr(t, t);
		return t;
	};
}
function $(e, t) {
	if (T) {
		var n = G;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = E), Le();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var yr = ["touchstart", "touchmove"];
function br(e) {
	return yr.includes(e);
}
function xr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[_e] ??= e.nodeValue) && (e[_e] = n, e.nodeValue = `${n}`);
}
function Sr(e, t) {
	return Tr(e, t);
}
function Cr(e, t) {
	rn(), t.intro = t.intro ?? !1;
	let n = t.target, i = T, a = E;
	try {
		for (var o = /* @__PURE__ */ on(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ sn(o);
		if (!o) throw r;
		Ie(!0), D(o);
		let i = Tr(e, {
			...t,
			anchor: o
		});
		return Ie(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && De(), rn(), cn(n), Ie(!1), Sr(e, t);
	} finally {
		Ie(i), D(a);
	}
}
var wr = /* @__PURE__ */ new Map();
function Tr(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	rn();
	var u = void 0, d = wn(() => {
		var s = n ?? t.appendChild(an());
		lt(s, { pending: () => {} }, (t) => {
			Ge({});
			var n = k;
			if (o && (n.c = o), a && (i.$$events = a), T && vr(t, null), u = e(t, i) || {}, T && (G.nodes.end = E, E === null || E.nodeType !== 8 || E.data !== "]")) throw Pe(), r;
			Ke();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = br(r);
					for (let e of [t, document]) {
						var a = wr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), wr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, mr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(lr)), ur.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = wr.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, mr), r.delete(e), r.size === 0 && wr.delete(n)) : r.set(e, i);
			}
			ur.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return Er.set(u, d), u;
}
var Er = /* @__PURE__ */ new WeakMap();
function Dr(e, t) {
	let n = Er.get(e);
	return n ? (Er.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Or = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) Ln(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (Ln(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (B(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						zn(r, t), t.append(an()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Fn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = j, r = ln();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = an();
			i.append(a), this.#n.set(e, {
				effect: z(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, z(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else T && (this.anchor = E), this.#a(n);
	}
};
function kr(e) {
	k === null && xe("onMount"), t && k.l !== null ? Ar(k).m.push(e) : bn(() => {
		let t = ar(e);
		if (typeof t == "function") return t;
	});
}
function Ar(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function jr(e, t, n = !1) {
	var r;
	T && (r = E, Le());
	var i = new Or(e), a = n ? se : 0;
	function o(e, t) {
		if (T) {
			var n = Be(r);
			if (e !== parseInt(n.substring(1))) {
				var a = ze();
				D(a), i.anchor = a, Ie(!1), i.ensure(e, t), Ie(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	kn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Mr(e, t) {
	Tn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = un("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Nr = Symbol("is custom element"), Pr = Symbol("is html"), Fr = be ? "link" : "LINK";
function Ir(e) {
	if (T) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					Lr(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					Lr(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ve] = n, Xe(n), pn();
	}
}
function Lr(e, t, n, r) {
	var i = zr(e);
	T && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Fr) || i[t] !== (i[t] = n) && (t === "loading" && (e[pe] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && Vr(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function Rr(e, t, n) {
	var r = H, i = G;
	let a = T;
	T && Ie(!1), W(null), K(null);
	try {
		t !== "style" && (Br.has(e.getAttribute("is") || e.nodeName) || !customElements || customElements.get(e.getAttribute("is") || e.nodeName.toLowerCase()) ? Vr(e).includes(t) : n && typeof n == "object") ? e[t] = n : Lr(e, t, n == null ? n : String(n));
	} finally {
		W(r), K(i), a && Ie(!0);
	}
}
function zr(e) {
	return e[me] ??= {
		[Nr]: e.nodeName.includes("-"),
		[Pr]: e.namespaceURI === a
	};
}
var Br = /* @__PURE__ */ new Map();
function Vr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Br.get(t);
	if (n) return n;
	Br.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function Hr(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	hn(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = Ur(t) ? Wr(a) : a, r(a), j !== null && i.add(j), await nr(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (T && t.defaultValue !== t.value || ar(n) == null && t.value) && (r(Ur(t) ? Wr(t.value) : t.value), j !== null && i.add(j)), Dn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? Et : j;
			if (i.has(a)) return;
		}
		Ur(t) && r === Wr(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function Ur(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function Wr(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Gr(e = !1) {
	let t = k, n = t.l.u;
	if (!n) return;
	let r = () => or(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ ht(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Z(i);
	}
	n.b.length && Sn(() => {
		Kr(t, r), y(n.b);
	}), bn(() => {
		let e = ar(() => n.m.map(ee));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && bn(() => {
		Kr(t, r), y(n.a);
	});
}
function Kr(e, t) {
	if (e.l.s) for (let t of e.l.s) Z(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function qr(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = void 0, d = () => s && a ? (u ??= /* @__PURE__ */ ht(i), Z(u)) : (l && (l = !1, c = s ? ar(i) : i), c);
	let p;
	if (o) {
		var m = w in e || fe in e;
		p = f(e, n)?.set ?? (m && n in e ? (t) => e[n] = t : void 0);
	}
	var h, g = !1;
	o ? [h, g] = ot(() => e[n]) : h = e[n], h === void 0 && i !== void 0 && (h = d(), p && (a && Oe(n), p(h)));
	var _ = a ? () => {
		var t = e[n];
		return t === void 0 ? d() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return _;
	if (p) {
		var v = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || v || g) && p(t ? _() : e), e) : _();
		});
	}
	var ee = !1, y = (r & 1 ? ht : vt)(() => (ee = !1, _()));
	o && Z(y);
	var te = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Z(y) : a && o ? Qt(e) : e;
			return F(y, n), ee = !0, c !== void 0 && (c = n), e;
		}
		return V && ee || te.f & 16384 ? y.v : Z(y);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function Jr(e) {
	return new Yr(e);
}
var Yr = class {
	#e;
	#t;
	constructor(t) {
		var n = /* @__PURE__ */ new Map(), r = (e, t) => {
			var r = /* @__PURE__ */ P(t, !1, !1);
			return n.set(e, r), r;
		};
		let i = new Proxy({
			...t.props || {},
			$$events: {}
		}, {
			get(e, t) {
				return Z(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === fe ? !0 : (Z(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
			},
			set(e, t, i) {
				return F(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? Cr : Sr)(t.component, {
			target: t.target,
			anchor: t.anchor,
			props: i,
			context: t.context,
			intro: t.intro ?? !1,
			recover: t.recover,
			transformError: t.transformError
		}), !e && (!t?.props?.$$host || t.sync === !1) && Ft(), this.#e = i.$$events;
		for (let e of Object.keys(this.#t)) e === "$set" || e === "$destroy" || e === "$on" || d(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(i, e);
		}, this.#t.$destroy = () => {
			Dr(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, Xr;
typeof HTMLElement == "function" && (Xr = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = un("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = Qr(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = Zr(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = Jr({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = Cn(() => {
				Dn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = Zr(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = Zr(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return u(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function Zr(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function Qr(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function $r(e, t, n, r, i, a) {
	let o = class extends Xr {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return u(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return u(t).forEach((e) => {
		d(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = Zr(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (f(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		d(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region PlexCard.svelte
var ei = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-lueg2f\">Active</span>"), ti = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-lueg2f\">Authenticated</span>"), ni = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-lueg2f\">Connected</span>"), ri = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-lueg2f\">Disconnected</span>"), ii = /* @__PURE__ */ Q("<div class=\"loading-state svelte-lueg2f\"><div class=\"spinner svelte-lueg2f\"></div> <span>Linking with Plex Nexus...</span></div>"), ai = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-lueg2f\"> </button>"), oi = /* @__PURE__ */ Q("<button class=\"btn-ghost accent svelte-lueg2f\"> </button>"), si = /* @__PURE__ */ Q("<button class=\"btn-danger-ghost svelte-lueg2f\">Cancel Authorization</button>"), ci = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-lueg2f\">Switch Account</button>"), li = /* @__PURE__ */ Q("<button class=\"btn-primary plex-btn svelte-lueg2f\"><svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"currentColor\"><path d=\"M12 0L9.33 6.67L2 9.33L7.33 14.67L6 22L12 18.67L18 22L16.67 14.67L22 9.33L14.67 6.67L12 0Z\"></path></svg> Sign in with Plex</button>"), ui = /* @__PURE__ */ Q("<div class=\"settings-section svelte-lueg2f\"><div class=\"form-grid svelte-lueg2f\"><div class=\"form-field svelte-lueg2f\"><span class=\"field-label svelte-lueg2f\">Server Access URL</span> <input type=\"text\" placeholder=\"http://192.168.1.100:32400\" class=\"input-field svelte-lueg2f\"/> <span class=\"helper-text svelte-lueg2f\">Typically http://[IP]:32400. Use localhost if running natively.</span></div> <div class=\"form-field svelte-lueg2f\"><span class=\"field-label svelte-lueg2f\">Friendly Name</span> <input type=\"text\" placeholder=\"e.g. Home Media\" class=\"input-field svelte-lueg2f\"/></div> <div class=\"path-mappings svelte-lueg2f\"><div class=\"mapping-header svelte-lueg2f\" style=\"display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;\"><span class=\"field-label svelte-lueg2f\" style=\"margin: 0;\">Path Mappings</span> <button class=\"btn-ghost-small svelte-lueg2f\"> </button></div> <div class=\"editor-wrapper\"><echosync-path-mapping-editor></echosync-path-mapping-editor></div></div> <div class=\"actions-row svelte-lueg2f\"><button class=\"btn-primary svelte-lueg2f\"> </button> <!> <!> <div class=\"auth-box svelte-lueg2f\"><!></div></div></div></div>", 2), di = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-lueg2f\"><div class=\"card-header svelte-lueg2f\"><div class=\"header-left svelte-lueg2f\"><h2 class=\"card-title svelte-lueg2f\">Plex Media Server</h2> <div class=\"badges svelte-lueg2f\"><!> <!> <!></div></div> <button class=\"btn-ghost-small svelte-lueg2f\"> </button></div> <!></section>"), fi = {
	hash: "svelte-lueg2f",
	code: "\n  /* SHADOW DOM STYLING */.plugin-card.svelte-lueg2f {background:var(--bg-surface);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);padding:24px;color:var(--text-primary);font-family:inherit;}.card-header.svelte-lueg2f {display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border-subtle);}.header-left.svelte-lueg2f {display:flex;align-items:center;gap:16px;}.card-title.svelte-lueg2f {margin:0;font-size:18px;font-weight:700;letter-spacing:-0.01em;}.badges.svelte-lueg2f {display:flex;gap:8px;}.status-badge.svelte-lueg2f {font-size:9px;padding:2px 8px;border-radius:5px;font-weight:800;text-transform:uppercase;letter-spacing:0.05em;}.status-badge.active.svelte-lueg2f {background:rgba(20, 184, 166, 0.1);color:var(--color-primary);border:1px solid rgba(20, 184, 166, 0.2);}.status-badge.success.svelte-lueg2f {background:rgba(16, 185, 129, 0.1);color:#10b981;border:1px solid rgba(16, 185, 129, 0.2);}.status-badge.warning.svelte-lueg2f {background:rgba(245, 158, 11, 0.1);color:#f59e0b;border:1px solid rgba(245, 158, 11, 0.2);}.btn-ghost.svelte-lueg2f, .btn-ghost-small.svelte-lueg2f, .btn-danger-ghost.svelte-lueg2f {padding:10px 18px;background:rgba(255, 255, 255, 0.04);border:1px solid var(--border-subtle);color:var(--text-primary);border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-ghost-small.svelte-lueg2f {padding:6px 12px;font-size:11px;border-radius:6px;}.btn-ghost.svelte-lueg2f:hover, .btn-ghost-small.svelte-lueg2f:hover {background:rgba(255, 255, 255, 0.08);border-color:rgba(255, 255, 255, 0.2);}.btn-ghost.accent.svelte-lueg2f {color:var(--color-primary);border-color:rgba(20, 184, 166, 0.3);}.btn-danger-ghost.svelte-lueg2f {color:#ef4444;border-color:rgba(239, 68, 68, 0.2);}.btn-primary.svelte-lueg2f {padding:10px 24px;background:var(--color-primary);color:#000;border:none;border-radius:10px;font-weight:700;font-size:14px;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-lueg2f:hover:not(:disabled) {filter:brightness(1.1);transform:translateY(-1px);}.plex-btn.svelte-lueg2f {display:flex;align-items:center;gap:8px;background:#e5a00d; /* Plex Gold */color:#000;}.loading-state.svelte-lueg2f {display:flex;flex-direction:column;align-items:center;gap:16px;padding:40px;color:var(--text-muted);}.spinner.svelte-lueg2f {width:28px;height:28px;border:3px solid rgba(255, 255, 255, 0.05);border-top-color:var(--color-primary);border-radius:50%;\n    animation: svelte-lueg2f-spin 1s linear infinite;}\n\n  @keyframes svelte-lueg2f-spin { to { transform: rotate(360deg); } }.settings-section.svelte-lueg2f {margin-top:8px;}.form-grid.svelte-lueg2f {display:flex;flex-direction:column;gap:20px;}.form-field.svelte-lueg2f {display:flex;flex-direction:column;gap:8px;}.field-label.svelte-lueg2f {font-size:12px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;}.input-field.svelte-lueg2f {width:100%;padding:12px 16px;background:var(--bg-input, #0b0f1a);border:1px solid var(--border-subtle);border-radius:10px;color:var(--text-primary);font-size:14px;transition:all 0.2s;}.input-field.svelte-lueg2f:focus {outline:none;border-color:var(--color-primary);box-shadow:0 0 0 3px rgba(20, 184, 166, 0.1);}.helper-text.svelte-lueg2f {font-size:11px;color:var(--text-muted);font-style:italic;}.path-mappings.svelte-lueg2f {padding:20px 0;border-top:1px solid rgba(255,255,255,0.05);}.mapping-header.svelte-lueg2f {margin-bottom:12px;}.actions-row.svelte-lueg2f {display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-top:8px;}.auth-box.svelte-lueg2f {margin-left:auto;}\n\n  @media (max-width: 600px) {.auth-box.svelte-lueg2f {margin-left:0;width:100%;}.auth-box.svelte-lueg2f button:where(.svelte-lueg2f) {width:100%;}\n  }"
};
function pi(e, t) {
	Ge(t, !1), Mr(e, fi);
	let n = qr(t, "apiBase", 12, ""), r = /* @__PURE__ */ P(""), i = /* @__PURE__ */ P(""), a = /* @__PURE__ */ P([]), o = /* @__PURE__ */ P(!1), s = /* @__PURE__ */ P(!1), c = /* @__PURE__ */ P(!0), l = /* @__PURE__ */ P(!1), u = /* @__PURE__ */ P(!1), d = /* @__PURE__ */ P(!1), f = null, p = null, m = /* @__PURE__ */ P(!1), h = /* @__PURE__ */ P(!1), g = /* @__PURE__ */ P(!1);
	kr(async () => {
		n(n().replace(/\/$/, "")), await v(), F(c, !1);
	});
	async function _() {
		try {
			if (F(g, !0), !(await fetch(`${n()}/activate`, { method: "POST" })).ok) throw Error("Activation failed");
			await v();
		} catch (e) {
			console.error("Failed to activate server:", e), alert("Activation failed. Check logs.");
		} finally {
			F(g, !1);
		}
	}
	async function v() {
		try {
			let e = await (await fetch(`${n()}/settings`)).json();
			e?.settings && (F(r, e.settings.base_url || ""), F(i, e.settings.server_name || ""), F(a, e.settings.path_mappings || []), F(o, e.settings.has_token || !1), F(s, e.settings.connected || !1), F(h, e.settings.is_active || !1));
		} catch (e) {
			console.error("Failed to load Plex settings:", e);
		}
	}
	async function ee() {
		if (!Z(r).trim()) {
			alert("Server URL is required");
			return;
		}
		try {
			if (F(l, !0), !(await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					base_url: Z(r),
					server_name: Z(i),
					path_mappings: Z(a)
				})
			})).ok) throw Error("Save failed");
			await v();
		} catch (e) {
			console.error("Failed to save Plex settings:", e), alert("Failed to save settings.");
		} finally {
			F(l, !1);
		}
	}
	async function y() {
		try {
			F(d, !0);
			let e = await (await fetch(`${n()}/auth/start`, { method: "POST" })).json();
			e?.oauth_url && e?.session_id && (f = e.session_id, window.open(e.oauth_url, "PlexOAuth", "width=600,height=700,menubar=no,status=no"), p = setInterval(async () => {
				try {
					(await (await fetch(`${n()}/auth/poll/${f}`)).json())?.completed && (clearInterval(p), p = null, F(d, !1), f = null, await v());
				} catch (e) {
					console.error("OAuth poll error:", e), e.status === 404 && (clearInterval(p), p = null, F(d, !1), f = null);
				}
			}, 3e3));
		} catch (e) {
			console.error("Failed to start Plex OAuth:", e), F(d, !1);
		}
	}
	async function te() {
		if (f && p) {
			clearInterval(p), p = null;
			try {
				await fetch(`${n()}/auth/cancel/${f}`, { method: "DELETE" });
			} catch (e) {
				console.error("Failed to cancel OAuth:", e);
			}
			f = null, F(d, !1);
		}
	}
	async function b() {
		try {
			F(u, !0), (await (await fetch(`${n()}/test-connection`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ base_url: Z(r) })
			})).json())?.connected ? (alert("Connection successful!"), await v()) : alert("Connection failed. Check URL and ensure Plex is running.");
		} catch (e) {
			console.error("Connection test failed:", e), alert("Test failed with error.");
		} finally {
			F(u, !1);
		}
	}
	let x = /* @__PURE__ */ P(!1);
	async function ne() {
		try {
			F(x, !0);
			let e = await (await fetch(`${n()}/auto-map-paths`, { method: "POST" })).json();
			if (e?.success && e.mappings) {
				let t = e.mappings.filter((e) => !Z(a).some((t) => t.remote === e.remote && t.local === e.local));
				t.length > 0 ? (F(a, [...Z(a), ...t]), await ee(), alert("Auto-mapping successful!")) : alert("Derived mapping is already configured.");
			} else alert("Auto-mapping failed: " + (e?.error || "Unknown error"));
		} catch (e) {
			console.error("Auto-mapping failed:", e), alert("Auto-mapping failed with error.");
		} finally {
			F(x, !1);
		}
	}
	var re = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Ft();
		}
	};
	Gr();
	var ie = di(), ae = I(ie), oe = I(ae), se = L(I(oe), 2), S = I(se), ce = (e) => {
		$(e, ei());
	};
	jr(S, (e) => {
		Z(h) && e(ce);
	});
	var C = L(S, 2), le = (e) => {
		$(e, ti());
	};
	jr(C, (e) => {
		Z(o) && e(le);
	});
	var ue = L(C, 2), de = (e) => {
		$(e, ni());
	}, w = (e) => {
		$(e, ri());
	};
	jr(ue, (e) => {
		Z(s) ? e(de) : Z(o) && e(w, 1);
	}), O(se), O(oe);
	var fe = L(oe, 2), pe = I(fe, !0);
	O(fe), O(ae);
	var me = L(ae, 2), he = (e) => {
		$(e, ii());
	}, ge = (e) => {
		var t = ui(), n = I(t), s = I(n), c = L(I(s), 2);
		Ir(c), Re(2), O(s);
		var f = L(s, 2), p = L(I(f), 2);
		Ir(p), O(f);
		var m = L(f, 2), v = I(m), re = L(I(v), 2), ie = I(re, !0);
		O(re), O(v);
		var ae = L(v, 2), oe = I(ae);
		On(() => Rr(oe, "mappings", (Z(a), ar(() => JSON.stringify(Z(a)))))), O(ae), O(m);
		var se = L(m, 2), S = I(se), ce = I(S, !0);
		O(S);
		var C = L(S, 2), le = (e) => {
			var t = ai(), n = I(t, !0);
			O(t), On((e) => {
				t.disabled = e, xr(n, Z(u) ? "Testing..." : "Test Connection");
			}, [() => (Z(u), Z(r), ar(() => Z(u) || !Z(r).trim()))]), fr("click", t, b), $(e, t);
		};
		jr(C, (e) => {
			Z(o) && e(le);
		});
		var ue = L(C, 2), de = (e) => {
			var t = oi(), n = I(t, !0);
			O(t), On(() => {
				t.disabled = Z(g), xr(n, Z(g) ? "Activating..." : "Activate for Sync");
			}), fr("click", t, _), $(e, t);
		};
		jr(ue, (e) => {
			!Z(h) && Z(o) && e(de);
		});
		var w = L(ue, 2), fe = I(w), pe = (e) => {
			var t = si();
			fr("click", t, te), $(e, t);
		}, me = (e) => {
			var t = ci();
			fr("click", t, y), $(e, t);
		}, he = (e) => {
			var t = li();
			fr("click", t, y), $(e, t);
		};
		jr(fe, (e) => {
			Z(d) ? e(pe) : Z(o) ? e(me, 1) : e(he, -1);
		}), O(w), O(se), O(n), O(t), On(() => {
			re.disabled = Z(x) || !Z(o), xr(ie, Z(x) ? "Analyzing..." : "Auto-Generate Mappings"), S.disabled = Z(l), xr(ce, Z(l) ? "Saving..." : "Save Configuration");
		}), Hr(c, () => Z(r), (e) => F(r, e)), Hr(p, () => Z(i), (e) => F(i, e)), fr("click", re, ne), fr("es-path-update", oe, (e) => F(a, e.detail)), fr("click", S, ee), $(e, t);
	};
	return jr(me, (e) => {
		Z(c) ? e(he) : Z(m) || e(ge, 1);
	}), O(ie), On(() => xr(pe, Z(m) ? "Expand" : "Collapse")), fr("click", fe, () => F(m, !Z(m))), $(e, ie), Ke(re);
}
customElements.define("plex-dashboard-card", $r(pi, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { pi as default };
